#!/usr/bin/env python3
"""Build script for Perfetto extension source files.

Reads config.yaml and source files from src/{module}/{feature}/:
  - src/{module}/sql_modules/*.sql   -> modules/{module}/sql_modules
  - src/{module}/macros/*.yaml       -> modules/{module}/macros
  - src/{module}/proto_descriptors/*.proto -> modules/{module}/proto_descriptors

Also generates the top-level manifest from discovered modules.
"""

import base64
import json
import os
import subprocess
import sys
import tempfile

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT, 'src')
MODULES_DIR = os.path.join(ROOT, 'modules')


def load_config() -> dict:
    with open(os.path.join(ROOT, 'config.yaml')) as f:
        return yaml.safe_load(f)


def collect_sql_modules(sql_dir: str, namespace: str) -> list:
    """Collect all .sql files (recursively) from sql_modules/ dir."""
    modules = []
    if not os.path.isdir(sql_dir):
        return modules
    for dirpath, _, filenames in os.walk(sql_dir):
        for fn in sorted(filenames):
            if not fn.endswith('.sql'):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), sql_dir)
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


def load_macro_file(filepath: str) -> dict:
    """Load a macro definition from a .yaml or .json file."""
    with open(filepath) as f:
        if filepath.endswith('.json'):
            return json.load(f)
        return yaml.safe_load(f)


def collect_macros(macros_dir: str) -> list:
    """Collect all .yaml/.json files from macros/ dir."""
    macros = []
    if not os.path.isdir(macros_dir):
        return macros
    entries = sorted(os.listdir(macros_dir))
    for fn in entries:
        if not fn.endswith('.yaml') and not fn.endswith('.json'):
            continue
        data = load_macro_file(os.path.join(macros_dir, fn))
        run = []
        for cmd in data.get('run', []):
            run.append({'id': cmd['id'], 'args': cmd.get('args', [])})
        macros.append({
            'id': data['id'],
            'name': data['name'],
            'run': run,
        })
    return macros


def collect_proto_descriptors(proto_dir: str) -> list:
    """Collect all .proto files from proto_descriptors/ dir, compile, and base64 encode."""
    descriptors = []
    if not os.path.isdir(proto_dir):
        return descriptors
    entries = sorted(os.listdir(proto_dir))
    proto_files = [fn for fn in entries if fn.endswith('.proto')]
    if not proto_files:
        return descriptors
    for fn in proto_files:
        filepath = os.path.join(proto_dir, fn)
        with tempfile.NamedTemporaryFile(suffix='.desc', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            subprocess.check_call([
                'protoc',
                f'--proto_path={proto_dir}',
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
        d for d in os.listdir(SRC_DIR)
        if os.path.isdir(os.path.join(SRC_DIR, d))
    )

    for module_name in module_names:
        src_module_dir = os.path.join(SRC_DIR, module_name)
        out_module_dir = os.path.join(MODULES_DIR, module_name)
        os.makedirs(out_module_dir, exist_ok=True)

        # SQL modules (from src/{module}/sql_modules/*.sql)
        sql_modules = collect_sql_modules(
            os.path.join(src_module_dir, 'sql_modules'), namespace)
        write_json(
            os.path.join(out_module_dir, 'sql_modules'),
            {'sql_modules': sql_modules},
        )

        # Macros (from src/{module}/macros/*.yaml, *.json)
        macros = collect_macros(
            os.path.join(src_module_dir, 'macros'))
        write_json(
            os.path.join(out_module_dir, 'macros'),
            {'macros': macros},
        )

        # Proto descriptors (from src/{module}/proto_descriptors/*.proto)
        proto_descs = collect_proto_descriptors(
            os.path.join(src_module_dir, 'proto_descriptors'))
        write_json(
            os.path.join(out_module_dir, 'proto_descriptors'),
            {'proto_descriptors': proto_descs},
        )

    # Always include all three feature types in manifest
    all_features = [
        {'name': 'macros'},
        {'name': 'sql_modules'},
        {'name': 'proto_descriptors'},
    ]

    manifest = {
        'name': ext_name,
        'namespace': namespace,
        'features': all_features,
        'modules': [{'name': m} for m in module_names],
    }
    write_json(os.path.join(ROOT, 'manifest'), manifest)

    print(f'Built {len(module_names)} modules: {", ".join(module_names)}')


if __name__ == '__main__':
    build()
