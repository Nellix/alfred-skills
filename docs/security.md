# Security model

The registry is deliberately static. GitHub provides repository authentication, review history,
branch protection, and HTTPS distribution. Alfred additionally verifies the generated index and
each file digest before an atomic local update.

This protects against broken partial downloads and accidental file replacement. It does not protect
against a compromised maintainer account, a malicious approved pull request, or compromise of the
GitHub trust boundary. Production releases should add an offline Ed25519-signed index, pinned root
keys in the app, revocation metadata, and reproducible release automation.

On-device validation remains mandatory even after review. Alfred restricts schemes, action names,
package syntax, parameter shapes, semantic targets, destructive labels, action count, file size,
catalog size, and revision rollback. Downloaded interactive skills always require user confirmation.
