# Perfetto Extensions

Create your own [Perfetto UI extensions](https://github.com/google/perfetto/discussions/3227).

## Getting started

1. Fork this repo, or [import it](https://github.com/new/import) if you want a private copy.

2. Edit `config.yaml` to set your extension's name and namespace:
   ```yaml
   name: My Extension
   namespace: com.example.myext
   ```

3. Add [SQL modules](https://perfetto.dev/docs/analysis/perfetto-sql-getting-started) as `.sql` files under `src/{module}/sql_modules/`.

   The filename determines the module name. For example, with namespace `com.example.myext`:
   - `src/default/sql_modules/helpers.sql` → `INCLUDE PERFETTO MODULE com.example.myext.helpers;`
   - `src/default/sql_modules/foo/bar.sql` → `INCLUDE PERFETTO MODULE com.example.myext.foo.bar;`

   You can organise SQL files into subdirectories — each path component becomes a dot-separated part of the module name.

4. Add [UI macros](https://perfetto.dev/docs/visualization/ui-automation) as `.yaml` files under `src/{module}/macros/`.

5. Push to `main`. A GitHub Action will build and commit the generated endpoint files automatically.

## Connecting to the Perfetto UI

1. Go to [Perfetto UI extension settings](https://ui.perfetto.dev/#!/settings/dev.perfetto.ExtensionServers).

2. Add your repo as a GitHub extension server.

### Private repos

If your repo is private, you'll need a GitHub personal access token:

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens) and generate a new token (fine-grained).
2. Scope it to your extension repo with **Contents: Read** permission.
3. Enter the token in the Perfetto UI extension settings when adding your server.
