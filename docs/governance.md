# Registry governance

The default branch is the publication channel. It should require pull requests, automated
validation, resolved review conversations, and at least one maintainer approval.

Reviewers evaluate:

1. privacy and parameter generalization;
2. action scope and confirmation policy;
3. compatibility claims and reproducible testing;
4. whether an existing canonical intent should be extended instead;
5. whether revision and skill versions are monotonic.

Emergency removal uses a pull request that deletes the skill and increments the catalog revision.
Clients retain their last valid catalog if a refresh fails. A future signed revocation list will
support faster production response independent of the default branch.
