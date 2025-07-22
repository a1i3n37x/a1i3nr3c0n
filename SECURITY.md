# Security Policy

## Legal & Ethical Use Policy

**AlienRecon is intended for educational purposes and for use ONLY on systems you are explicitly authorized to test.**

Using this tool against networks or systems without prior mutual consent is illegal. The developers of AlienRecon assume no liability and are not responsible for any misuse or damage caused by this program. By using this tool, you acknowledge that you are using it in a responsible manner and in an environment you have permission to assess.

---

## Known Vulnerabilities

### Cryptography Package (as of June 2025)

The project currently has two known vulnerabilities in the `cryptography` package:
- GHSA-h4gh-qq45-vh27 (requires cryptography >= 43.0.1)
- GHSA-79v4-65xg-pq4g (requires cryptography >= 44.0.1)

**Why we can't update**: The `impacket` library (version 0.12.0) requires `pyopenssl==24.0.0`, which in turn requires `cryptography<43`. This prevents us from updating to the fixed versions.

**Impact**: These vulnerabilities affect cryptographic operations. Review the specific CVEs to understand if your use case is affected.

**Mitigation**:
1. The SMB enumeration functionality (which uses impacket) is isolated to the `smb.py` tool
2. Consider using alternative SMB enumeration tools if these vulnerabilities are critical for your environment
3. Monitor impacket for updates that support newer cryptography versions

## Reporting Vulnerabilities

If you discover a security vulnerability in AlienRecon, please:
1. **Do not** open a public issue
2. Email security concerns to the maintainer
3. Include steps to reproduce if possible
4. Allow reasonable time for a fix before public disclosure

## Security Best Practices

When using AlienRecon:
1. **Authorized Use**: Always ensure you have explicit, documented authorization before scanning or testing any system.
2. **API Key Security**: Keep your OpenAI API key secure and never commit it to version control. Use environment variables as recommended.
3. **Isolated Environments**: Run the tool in a contained environment (like the provided Docker container) to prevent unintended impact.
4. **Dependency Updates**: Regularly update dependencies when possible by rebuilding your Docker image or running `poetry update`.
