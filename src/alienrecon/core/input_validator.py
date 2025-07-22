# src/alienrecon/core/input_validator.py
"""Input validation and sanitization for security."""

import ipaddress
import logging
import re
import shlex
import socket
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse

from .exceptions import SecurityError, ValidationError

logger = logging.getLogger(__name__)


class InputValidator:
    """Validates and sanitizes user inputs for security."""

    # Regex patterns for validation
    HOSTNAME_PATTERN = re.compile(
        r"^(?=.{1,253}$)(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\.[a-zA-Z0-9-]{1,63})*$"
    )
    PORT_PATTERN = re.compile(r"^\d{1,5}$")

    # Dangerous command patterns
    DANGEROUS_PATTERNS = [
        r";\s*rm\s+-rf",  # rm -rf commands
        r";\s*dd\s+",  # dd commands
        r">\s*/dev/",  # Writing to devices
        r"`[^`]+`",  # Command substitution
        r"\$\([^)]+\)",  # Command substitution
        r"&&\s*curl",  # Command chaining with curl
        r"&&\s*wget",  # Command chaining with wget
        r"\|\s*sh",  # Piping to shell
        r"\|\s*bash",  # Piping to bash
    ]

    @classmethod
    def validate_target(cls, target: str) -> str:
        """Validate and sanitize a target IP or hostname."""
        if not target:
            raise ValidationError("Target cannot be empty")

        target = target.strip()

        # Try to parse as IP address first
        try:
            ip = ipaddress.ip_address(target)
            # Check for private/reserved IPs if needed
            if ip.is_loopback and target != "127.0.0.1":
                raise ValidationError(
                    "Loopback addresses other than 127.0.0.1 are not allowed"
                )
            return str(ip)
        except ValueError:
            # Not a valid IP, check if it looks like an invalid IP
            if re.match(r"^\d+(\.\d+){3}$", target):
                # It looks like an IP but isn't valid
                raise ValidationError(f"Invalid IP address: {target}")

        # Try to parse as hostname
        if cls.HOSTNAME_PATTERN.match(target):
            return target

        raise ValidationError(f"Invalid target format: {target}")

    @classmethod
    def validate_port(cls, port: Union[str, int]) -> int:
        """Validate a port number."""
        try:
            port_num = int(port)
            if 1 <= port_num <= 65535:
                return port_num
            raise ValidationError(f"Port must be between 1 and 65535, got {port_num}")
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid port: {port}")

    @classmethod
    def validate_port_list(cls, ports: str) -> str:
        """Validate a comma-separated list of ports or port ranges."""
        if not ports:
            raise ValidationError("Port list cannot be empty")

        validated_parts = []
        for part in ports.split(","):
            part = part.strip()
            if "-" in part:
                # Port range
                start, end = part.split("-", 1)
                start_port = cls.validate_port(start)
                end_port = cls.validate_port(end)
                if start_port > end_port:
                    raise ValidationError(f"Invalid port range: {part}")
                validated_parts.append(f"{start_port}-{end_port}")
            else:
                # Single port
                validated_parts.append(str(cls.validate_port(part)))

        return ",".join(validated_parts)

    @classmethod
    def validate_file_path(cls, path: str, must_exist: bool = False) -> Path:
        """Validate a file path."""
        try:
            # Check for path traversal attempts before resolving
            if ".." in path:
                raise SecurityError("Path traversal detected")

            path_obj = Path(path).resolve()

            if must_exist and not path_obj.exists():
                raise ValidationError(f"Path does not exist: {path}")

            return path_obj
        except SecurityError:
            raise  # Re-raise security errors
        except Exception as e:
            raise ValidationError(f"Invalid path: {path} - {e}")

    @classmethod
    def sanitize_command_args(cls, args: str) -> list[str]:
        """Sanitize command arguments for subprocess execution."""
        if not args:
            return []

        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, args, re.IGNORECASE):
                raise SecurityError("Potentially dangerous command pattern detected")

        # Use shlex to safely split arguments
        try:
            return shlex.split(args)
        except ValueError as e:
            raise ValidationError(f"Invalid command arguments: {e}")

    @classmethod
    def validate_url(cls, url: str) -> str:
        """Validate and sanitize a URL."""
        if not url:
            raise ValidationError("URL cannot be empty")

        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in ("http", "https", "ftp"):
                raise ValidationError(f"Unsupported URL scheme: {parsed.scheme}")

            # Check for basic validity
            if not parsed.netloc:
                raise ValidationError("URL must include a domain")

            # Reconstruct URL to ensure it's properly formatted
            return parsed.geturl()
        except Exception as e:
            raise ValidationError(f"Invalid URL: {url} - {e}")

    @classmethod
    def validate_username(cls, username: str) -> str:
        """Validate a username."""
        if not username:
            raise ValidationError("Username cannot be empty")

        # Basic validation - alphanumeric, underscore, dash, dot
        if not re.match(r"^[a-zA-Z0-9._-]+$", username):
            raise ValidationError("Username contains invalid characters")

        if len(username) > 64:
            raise ValidationError("Username too long (max 64 characters)")

        return username

    @classmethod
    def validate_wordlist_path(cls, path: str) -> Path:
        """Validate a wordlist file path."""
        path_obj = cls.validate_file_path(path, must_exist=True)

        # Check file extension
        if path_obj.suffix not in (".txt", ".lst", ".list"):
            raise ValidationError("Wordlist must be a .txt, .lst, or .list file")

        # Check file size (prevent loading huge files)
        max_size = 100 * 1024 * 1024  # 100MB
        if path_obj.stat().st_size > max_size:
            raise ValidationError("Wordlist file too large (max 100MB)")

        return path_obj

    @classmethod
    def resolve_and_validate_target(
        cls,
        target: Optional[str],
        fallback_ip: Optional[str] = None,
        fallback_hostname: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Resolve and validate a target address with DNS resolution and fallback logic.

        Args:
            target: The target address (IP or hostname) to resolve
            fallback_ip: Fallback IP address if target is invalid/empty
            fallback_hostname: Fallback hostname if target is invalid/empty

        Returns:
            Tuple of (resolved_ip, hostname) where either may be None
        """
        logger.debug(
            f"Resolving target: '{target}' with fallbacks: IP='{fallback_ip}', Host='{fallback_hostname}'"
        )

        # Handle empty/None target
        if not target:
            if fallback_ip:
                logger.debug(f"Using fallback IP: {fallback_ip}")
                return fallback_ip, fallback_hostname
            elif fallback_hostname:
                # Try to resolve fallback hostname
                resolved_ip = cls.resolve_hostname(fallback_hostname)
                if resolved_ip:
                    logger.debug(
                        f"Resolved fallback hostname '{fallback_hostname}' to {resolved_ip}"
                    )
                    return resolved_ip, fallback_hostname
            logger.warning("No valid target or fallback provided")
            return None, None

        target = target.strip()

        # Check if it's already a valid IP
        if cls.is_valid_ip(target):
            logger.debug(f"Target '{target}' is a valid IP address")
            # Try reverse DNS lookup
            hostname = cls.reverse_dns_lookup(target)
            return target, hostname

        # Check if it's a valid CIDR notation
        if cls.is_valid_cidr(target):
            logger.debug(f"Target '{target}' is a valid CIDR notation")
            return target, target  # Use CIDR as both IP and hostname

        # Check if it's a valid hostname
        if cls.is_valid_hostname(target):
            logger.debug(f"Target '{target}' appears to be a hostname")
            # Try to resolve it
            resolved_ip = cls.resolve_hostname(target)
            if resolved_ip:
                logger.debug(f"Resolved hostname '{target}' to {resolved_ip}")
                return resolved_ip, target
            else:
                logger.warning(f"Failed to resolve hostname '{target}'")
                # Check fallbacks
                if fallback_ip:
                    return fallback_ip, target
                elif fallback_hostname and fallback_hostname != target:
                    resolved_ip = cls.resolve_hostname(fallback_hostname)
                    if resolved_ip:
                        return resolved_ip, fallback_hostname

        logger.error(f"Could not resolve or validate target: '{target}'")
        return None, None

    @classmethod
    def is_valid_ip(cls, address: str) -> bool:
        """Check if a string is a valid IP address."""
        try:
            ipaddress.ip_address(address)
            return True
        except ValueError:
            return False

    @classmethod
    def is_valid_cidr(cls, address: str) -> bool:
        """Check if a string is a valid CIDR notation."""
        try:
            ipaddress.ip_network(address, strict=False)
            return True
        except ValueError:
            return False

    @classmethod
    def is_valid_hostname(cls, hostname: str) -> bool:
        """Check if a string looks like a valid hostname."""
        return bool(cls.HOSTNAME_PATTERN.match(hostname))

    @classmethod
    def resolve_hostname(cls, hostname: str) -> Optional[str]:
        """
        Resolve a hostname to an IP address using DNS.

        Args:
            hostname: The hostname to resolve

        Returns:
            The resolved IP address or None if resolution fails
        """
        try:
            # Socket.gethostbyname returns the primary IP
            ip_address = socket.gethostbyname(hostname)
            logger.info(f"Resolved '{hostname}' to {ip_address}")
            return ip_address
        except socket.gaierror as e:
            logger.warning(f"DNS resolution failed for '{hostname}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error resolving '{hostname}': {e}")
            return None

    @classmethod
    def reverse_dns_lookup(cls, ip_address: str) -> Optional[str]:
        """
        Perform reverse DNS lookup on an IP address.

        Args:
            ip_address: The IP address to look up

        Returns:
            The resolved hostname or None if lookup fails
        """
        try:
            hostname, _, _ = socket.gethostbyaddr(ip_address)
            logger.info(f"Reverse DNS for {ip_address}: {hostname}")
            return hostname
        except socket.herror:
            logger.debug(f"No reverse DNS entry for {ip_address}")
            return None
        except Exception as e:
            logger.error(f"Error in reverse DNS lookup for {ip_address}: {e}")
            return None

    @classmethod
    def resolve_multiple_targets(
        cls, targets: list[str]
    ) -> list[tuple[str, Optional[str]]]:
        """
        Resolve multiple targets in batch.

        Args:
            targets: List of target addresses (IPs or hostnames)

        Returns:
            List of (resolved_ip, hostname) tuples
        """
        results = []
        for target in targets:
            ip, hostname = cls.resolve_and_validate_target(target)
            if ip:
                results.append((ip, hostname))
            else:
                logger.warning(f"Skipping invalid target: {target}")
        return results

    @staticmethod
    def validate_custom_arguments(args: str, tool_name: str) -> str:
        """
        Validate custom command arguments for security.

        Args:
            args: Custom arguments string
            tool_name: Name of the tool for context-specific validation

        Returns:
            Validated arguments string

        Raises:
            ValidationError: If arguments are invalid or dangerous
        """
        import shlex

        if not args:
            return ""

        # Remove leading/trailing whitespace
        args = args.strip()

        # Check for dangerous shell operators
        dangerous_operators = [
            ";",
            "&&",
            "||",
            "|",
            "`",
            "$(",
            ">",
            ">>",
            "<",
            "$(",
            "${",
            "\n",
            "\r",
            "\x00",
        ]

        for op in dangerous_operators:
            if op in args:
                raise ValidationError(
                    f"Custom arguments contain dangerous operator '{op}'"
                )

        # Try to parse as shell arguments to ensure they're valid
        try:
            parsed = shlex.split(args)
        except ValueError as e:
            raise ValidationError(f"Invalid shell argument syntax: {e}")

        # Tool-specific validation
        if tool_name == "nmap":
            # Disallow output redirection in nmap
            disallowed = ["-oG", "-oN", "-oS", "-oX", "-oA", "--append-output"]
            for arg in parsed:
                if arg in disallowed or arg.startswith(tuple(disallowed)):
                    raise ValidationError(
                        f"Output redirection arguments not allowed: {arg}"
                    )

        elif tool_name == "ffuf":
            # Disallow output redirection in ffuf
            disallowed = ["-o", "-of", "-od"]
            for arg in parsed:
                if arg in disallowed:
                    raise ValidationError(
                        f"Output redirection arguments not allowed: {arg}"
                    )

        # Length check
        if len(args) > 500:
            raise ValidationError("Custom arguments too long (max 500 characters)")

        return args
