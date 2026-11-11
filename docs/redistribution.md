# Redistribution gate and notice inventory

The wrapper's root MIT license covers the component/template-derived code.
It does **not** license `oidc-cli` or automatically grant permission to
redistribute an executable merely because its GitHub repository is public.

At both development commit `27dd05ce90c0ecf0487a99d0e030e9d3a89ef37d` and
published `v0.1.1` commit `1c909c00e6aa4924c4755e325f8ba8bb25927b31`, no root
LICENSE/NOTICE/COPYRIGHT or README redistribution grant was found. The user/upstream maintainer must select
and publish the CLI's redistribution license separately. This wrapper does not
choose or add that license on their behalf. Production acquisition requires
reviewed upstream, dependency and runtime notice files and their SHA256 pins.
Until permission and those files are reviewed, acquisition/bundling remains
blocked. A signed published binary is now available and verified (`v0.1.1`);
signing is no longer the blocker.

Inventory from that commit's exact `go.mod` (not a claim of completed legal
review of a future binary):

| Component | Version / pin | Observed baseline license | Required release review |
| --- | --- | --- | --- |
| `github.com/miyako/oidc-cli` | exact future approved signed release; development SHA above | **Unresolved** | User-selected root redistribution permission and copyright notices |
| `github.com/coreos/go-oidc/v3` | `v3.21.0` | [Apache-2.0](https://github.com/coreos/go-oidc/blob/v3.21.0/LICENSE) | Full license and any applicable NOTICE/copyright material |
| `golang.org/x/oauth2` | `v0.38.0` | [BSD-3-Clause](https://github.com/golang/oauth2/blob/v0.38.0/LICENSE) | Copyright, conditions and disclaimer |
| `github.com/go-jose/go-jose/v4` | `v4.1.9` | [Apache-2.0](https://github.com/go-jose/go-jose/blob/v4.1.9/LICENSE) | Full license and applicable NOTICE/copyright material |
| Go runtime/standard library | toolchain `go1.26.10`, source minimum `go 1.26.0` | [Go BSD-style license](https://github.com/golang/go/blob/go1.26.10/LICENSE) | Baseline notice plus applicable bundled third-party/runtime exceptions for actual build settings |
| 4D tool4d | 20.7/101905 local validation only | Vendor terms | Do not bundle the compiler/runtime tool |

The component currently retains the template's Go baseline notice in
`Resources/licenses/Go-LICENSE.txt`; file presence alone is not a complete
dependency/runtime audit. Reconcile this inventory against the exact upstream
release's module graph/build metadata, any vendored sources, platform libraries
and additional NOTICE files before populating the reviewed production pin.
Do not silently treat the development-only archive as redistributable or
substitute this inventory for the required full notices.
