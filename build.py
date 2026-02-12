#!/usr/bin/env python3
"""Build script for Perfetto extension source files.

Reads config.yaml and source files (.sql, .yaml, .proto) from modules/,
and generates JSON endpoint files (sql_modules, macros, proto_descriptors)
plus the top-level manifest.
"""

import base64
import json
import os
import subprocess
import sys
import tempfile

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(ROOT, 'modules')

GENERATED_FILES = {'sql_modules', 'macros', 'proto_descriptors', 'manifest'}


def to_pascal_case(name: str) -> str:
    """Convert a snake_case name to PascalCase."""
    return ''.join(word.capitalize() for word in name.split('_'))


def load_config() -> dict:
    with open(os.path.join(ROOT, 'config.yaml')) as f:
        return yaml.safe_load(f)


def collect_sql_modules(module_dir: str, namespace: str) -> list:
    """Collect all .sql files (recursively) and produce sql_module entries."""
    modules = []
    for dirpath, _, filenames in os.walk(module_dir):
        for fn in sorted(filenames):
            if not fn.endswith('.sql'):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), module_dir)
            # Convert path to dot-separated module name:
            # e.g. "foo/bar.sql" -> "foo.bar", "common.sql" -> "common"
            parts = rel.replace(os.sep, '/').split('/')
            parts[-1] = parts[-1][:-4]  # strip .sql
            suffix = '.'.join(parts)
            name = f'{namespace}.{suffix}'
            with open(os.path.join(dirpath, fn)) as f:
                sql = f.read().rstrip('\n')
            modules.append({'name': name, 'sql': sql})
    modules.sort(key=lambda m: m['name'])
    return modules


def collect_macros(module_dir: str, namespace: str) -> list:
    """Collect all .yaml files in the module directory (flat) and produce macro entries."""
    macros = []
    entries = sorted(os.listdir(module_dir))
    for fn in entries:
        if not fn.endswith('.yaml'):
            continue
        filepath = os.path.join(module_dir, fn)
        with open(filepath) as f:
            data = yaml.safe_load(f)
        basename = fn[:-5]  # strip .yaml
        macro_id = f'{namespace}.{to_pascal_case(basename)}'
        commands = data.get('commands', [])
        run = []
        for cmd in commands:
            entry = {'id': cmd['id'], 'args': cmd.get('args', [])}
            run.append(entry)
        macros.append({
            'id': macro_id,
            'name': data['name'],
            'run': run,
        })
    return macros


def collect_proto_descriptors(module_dir: str) -> list:
    """Collect all .proto files in the module directory (flat), compile, and base64 encode."""
    descriptors = []
    entries = sorted(os.listdir(module_dir))
    proto_files = [fn for fn in entries if fn.endswith('.proto')]
    if not proto_files:
        return descriptors
    for fn in proto_files:
        filepath = os.path.join(module_dir, fn)
        with tempfile.NamedTemporaryFile(suffix='.desc', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            subprocess.check_call([
                'protoc',
                f'--proto_path={module_dir}',
                f'--descriptor_set_out={tmp_path}',
                filepath,
            ])
            with open(tmp_path, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode('ascii')
            descriptors.append(encoded)
        except FileNotFoundError:
            print(f'Warning: protoc not found, skipping {fn}', file=sys.stderr)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    return descriptors


def write_json(path: str, data) -> None:
    """Write JSON with consistent formatting (2-space indent, trailing newline)."""
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')


def build():
    config = load_config()
    namespace = config['namespace']
    ext_name = config['name']

    module_names = sorted(
        d for d in os.listdir(MODULES_DIR)
        if os.path.isdir(os.path.join(MODULES_DIR, d))
    )

    features = set()
    for module_name in module_names:
        module_dir = os.path.join(MODULES_DIR, module_name)

        # SQL modules
        sql_modules = collect_sql_modules(module_dir, namespace)
        write_json(
            os.path.join(module_dir, 'sql_modules'),
            {'sql_modules': sql_modules},
        )
        if sql_modules:
            features.add('sql_modules')

        # Macros
        macros = collect_macros(module_dir, namespace)
        write_json(
            os.path.join(module_dir, 'macros'),
            {'macros': macros},
        )
        if macros:
            features.add('macros')

        # Proto descriptors
        proto_descs = collect_proto_descriptors(module_dir)
        write_json(
            os.path.join(module_dir, 'proto_descriptors'),
            {'proto_descriptors': proto_descs},
        )
        if proto_descs:
            features.add('proto_descriptors')

    # Always include all three feature types in manifest
    all_features = ['macros', 'sql_modules', 'proto_descriptors']

    manifest = {
        'name': ext_name,
        'namespace': namespace,
        'features': all_features,
        'modules': module_names,
    }
    write_json(os.path.join(ROOT, 'manifest'), manifest)

    print(f'Built {len(module_names)} modules: {", ".join(module_names)}')


if __name__ == '__main__':
    build()
