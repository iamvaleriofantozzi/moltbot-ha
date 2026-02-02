# Changelog

All notable changes to moltbot-ha will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-29

### Added
- Initial release of moltbot-ha
- Core commands: `list`, `state`, `on`, `off`, `toggle`, `set`, `call`
- Configuration management: `config init`, `config show`
- 3-level safety system with configurable confirmation workflows
- Critical domain protection (lock, alarm_control_panel, cover)
- Allowlist/blocklist support with wildcard patterns
- Comprehensive error handling and retry logic
- Action logging to file
- JSON and table output formats
- Environment variable configuration override
- Connection testing: `test` command
- Docker-friendly design for Moltbot integration
- Full documentation (SKILL.md for agents, README.md for humans)

### Security
- Safety level 3 (default): requires explicit `--force` for critical actions
- Blocked entities cannot be controlled even with `--force`
- Token stored in environment variable (not in config file)
- All actions logged with timestamps

## [Unreleased]

### Planned
- WebSocket support for real-time entity updates
- Entity state caching to reduce API calls
- Auto-discovery via mDNS/zeroconf
- Bash/Zsh completion scripts
- Unit and integration test suite
- CI/CD pipeline
- PyPI publication

---

[0.1.0]: https://github.com/iamvaleriofantozzi/moltbot-ha/releases/tag/v0.1.0
