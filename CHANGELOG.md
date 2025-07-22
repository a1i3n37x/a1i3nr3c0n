# Changelog

All notable changes to AlienRecon will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Complete Model Context Protocol (MCP) integration
- Support for Python 3.11, 3.12, and 3.13
- Docker containerization with security hardening
- Comprehensive CI/CD pipeline with GitHub Actions
- Enhanced error handling with AI guidance
- CTF-specific features and mission folders
- Flag detection and celebration
- Dry-run mode for command preview
- Session persistence and recovery
- Cache system for efficient operations
- Debrief report generation

### Changed
- Migrated from OpenAI function calling to MCP architecture
- Updated Poetry configuration to PEP 621 standard
- Refactored session controller for better state management
- Improved security validation and input sanitization
- Enhanced tool error messages with troubleshooting guidance

### Fixed
- Test suite failures after MCP migration
- Poetry deprecation warnings
- Command injection vulnerabilities
- Session state corruption issues

### Removed
- OpenAI function calling implementation
- Legacy test files from pre-refactoring
- Deprecated configuration options

## [1.0.0] - TBD

### Notes
- First stable release
- Production-ready for CTF and security assessment workflows
- Full MCP integration with all security tools
- Comprehensive documentation and examples

### Known Issues
- Cryptography package vulnerabilities due to impacket 0.12.0 compatibility
- Some experimental tests have minor warnings

### Contributors
- @a1i3n37x - Project creator and maintainer

---

For detailed release notes, see the [GitHub Releases](https://github.com/a1i3n37x/a37/releases) page.
