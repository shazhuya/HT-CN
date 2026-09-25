# M9 post-release — Windows source Web freshness v1

status: implementing

A Git checkout must not serve a Web bundle built from a different commit.

Contract:
1. In a Git checkout, current HEAD is the source-build identity.
2. apps/web/dist/.htcn-build-head records the HEAD that produced the built Web.
3. Missing marker, missing dist/index.html, or marker != current HEAD triggers install/rebuild before supervisor startup.
4. Successful source build writes the marker.
5. Packaged releases without .git keep the existing zero-Node daily-operation contract.
6. Recognition code is out of scope.
