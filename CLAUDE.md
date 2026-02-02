# Claude Code Instructions

**Read first**: [docs/SESSION_GUIDE.md](docs/SESSION_GUIDE.md) - contains all AI behavior rules.

## Quick Rules

- **Secrets**: Never write to git-tracked files (live in `.env.local`, Vercel, AWS Lambda)
- **Tests**: Colocate at `<module>/__tests__/test_*.py`
- **CSS**: Use component prefixes (`s1-`, `fm-`, `token-`)
- **dev.sh**: Use `jbe`, `jfe`, `jdbcreate`, `jpushapi` etc. instead of raw commands
- **API changes**: Update `docs/architecture/API_DESIGN.md` immediately after implementation
