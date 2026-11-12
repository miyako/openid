# Redistribution permission and notice provenance

The wrapper's root MIT license covers the component/template-derived code.
The separately maintained CLI has its own MIT owner grant and third-party terms;
public repository visibility alone is not redistribution permission.

The owner explicitly authorized MIT licensing of `miyako/oidc-cli`, including
the existing **v0.1.1 source and already-published release binaries**. The public
grant is recorded at immutable licensing commit
[`847a235a3cc02d82b4f3b432e5eb42c7cab5d3fc`](https://github.com/miyako/oidc-cli/commit/847a235a3cc02d82b4f3b432e5eb42c7cab5d3fc),
proposed in [miyako/oidc-cli#6](https://github.com/miyako/oidc-cli/pull/6).
It expressly permits wrapper bundling of the release built from source commit
`1c909c00e6aa4924c4755e325f8ba8bb25927b31`. Neither the earlier source tag nor its
binary-only archives contained these supplemental documents; fetch them from
the licensing commit, not the v0.1.1 tag. No tag or signed asset was replaced.

## Exact notices

[`scripts/oidc-cli-pin.json`](../scripts/oidc-cli-pin.json) records each original
URL and SHA256. These byte-exact files are committed under `scripts/licenses/`
and copied unchanged into the component's `Resources/licenses/` during assembly:

| Bundled filename | Upstream original / role |
| --- | --- |
| `OIDC-CLI-LICENSE.txt` | `LICENSE`: MIT, Copyright 2026 Keisuke Miyako |
| `OIDC-CLI-RELEASE-GRANT.txt` | `docs/license-grant.md`: explicit existing-release grant |
| `OIDC-CLI-THIRD-PARTY-NOTICES.txt` | `THIRD_PARTY_NOTICES.txt`: full dependency and Go runtime/toolchain notices |
| `OIDC-CLI-NOTICE-MANIFEST.json` | `third_party/manifest.json`: 43 original files, versions, paths and hashes |
| `OIDC-CLI-LICENSING-SCOPE.txt` | `docs/licensing.md`: exact inventory and conservative scope |
| `OIDC-CLI-Go-LICENSE.txt` | Exact Go1.26.10 baseline `LICENSE`, matching the upstream notice manifest |

The five upstream documents retain their original bytes, including whitespace
and references to original upstream filenames. The table maps those references
to the flattened component notice filenames; the component's separate root
license is packaged as `Resources/licenses/LICENSE`.

The combined notice bundle includes Go BSD terms and PATENTS, stdlib/vendor
and embedded third-party licenses, CoreOS Apache-2.0 LICENSE/NOTICE, go-jose's
Apache-2.0 root license and embedded `json/LICENSE`, and oauth2 BSD terms.
Its conservative inventory includes unused tool/test material from the complete
pinned toolchain and module distributions; inclusion does not claim that every
listed file is linked into the executable. Third-party code is not relicensed
under MIT.

## Reviewed build inventory

The exact signed binary's `go version -m` metadata identifies Go1.26.10,
`CGO_ENABLED=0`, and these three linked module versions, matching the upstream
notice inventory:

| Component | Version | Terms |
| --- | --- | --- |
| `github.com/miyako/oidc-cli` | v0.1.1, exact source and licensing commits above | MIT owner grant |
| `github.com/coreos/go-oidc/v3` | v3.21.0 | Apache-2.0 and NOTICE |
| `github.com/go-jose/go-jose/v4` | v4.1.9 | Apache-2.0; embedded JSON BSD terms |
| `golang.org/x/oauth2` | v0.38.0 | BSD-3-Clause |
| Go runtime/standard library | go1.26.10 | Go BSD-style license, patent grant and collected third-party terms |
| 4D tool4d | 20.7/101905, local validation only | Vendor terms; never bundled |

Production pin validation requires upstream, dependency and runtime records.
Every notice hash is checked before acquisition, assembly and packaging;
publication independently verifies the embedded archive bytes. Missing or
changed notices still fail closed. Re-review source, binary build metadata and
notice inventory whenever the upstream CLI, Go toolchain or modules change.
