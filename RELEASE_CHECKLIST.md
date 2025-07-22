# Release Checklist for AlienRecon

This checklist should be followed for each release to ensure quality and consistency.

## Pre-Release Checklist

### Code Quality
- [ ] All tests pass (`poetry run pytest`)
- [ ] Linting passes (`poetry run ruff check .`)
- [ ] Code is properly formatted (`poetry run ruff format .`)
- [ ] Type checking passes (`poetry run mypy src/`)
- [ ] Security audit reviewed (`poetry run pip-audit`)
- [ ] Test coverage is acceptable (aim for >70%)

### Documentation
- [ ] README.md is up to date
- [ ] CHANGELOG.md updated with release notes
- [ ] API documentation reflects any changes
- [ ] Installation instructions tested
- [ ] Docker instructions verified
- [ ] CTF mode documentation current

### Version Management
- [ ] Version bumped in `pyproject.toml`
- [ ] Version tag follows semantic versioning (vX.Y.Z)
- [ ] Git tag created and pushed

### Testing
- [ ] Manual testing on Linux
- [ ] Manual testing on macOS (if possible)
- [ ] Docker image builds successfully
- [ ] Docker container runs all commands
- [ ] MCP servers start correctly
- [ ] All tools execute properly
- [ ] Session persistence works
- [ ] CTF mode initialization works

## Release Process

1. **Update Version**
   ```bash
   # Update version in pyproject.toml
   poetry version <major|minor|patch>
   ```

2. **Update CHANGELOG**
   - Move unreleased items to new version section
   - Add release date
   - Review and finalize notes

3. **Create PR**
   ```bash
   git checkout -b release/vX.Y.Z
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore: prepare release vX.Y.Z"
   git push origin release/vX.Y.Z
   ```

4. **After PR Merge**
   ```bash
   git checkout main
   git pull origin main
   git tag -a vX.Y.Z -m "Release version X.Y.Z"
   git push origin vX.Y.Z
   ```

5. **Verify Release**
   - [ ] GitHub Actions release workflow runs
   - [ ] Docker image published to ghcr.io
   - [ ] Release artifacts uploaded
   - [ ] Release notes published

## Post-Release

- [ ] Announce release on social media
- [ ] Update Alien37.com if needed
- [ ] Monitor for immediate issues
- [ ] Plan next release milestones

## Versioning Strategy

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Incompatible API changes
- **MINOR** (0.X.0): New functionality, backwards compatible
- **PATCH** (0.0.X): Bug fixes, backwards compatible

### Examples:
- Breaking MCP changes: 2.0.0
- New tool added: 1.1.0
- Bug fix in nmap parser: 1.0.1

## Emergency Hotfix Process

1. Create hotfix branch from tag
2. Fix issue with minimal changes
3. Test thoroughly
4. Release as patch version
5. Cherry-pick to main if needed
