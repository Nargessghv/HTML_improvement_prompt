# Development Setup Guide

This guide explains how to set up the development environment for the Ekona Slide Creator frontend.

## Prerequisites

- Node.js 18+ and npm
- VS Code (recommended)
- Git

## Initial Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your configuration
   ```

3. **Set up Git hooks (since git repo is in parent directory):**
   ```bash
   # Run from the parent directory (Powerpoint Slide Creator)
   cd ..
   npx husky init
   npx husky add .husky/pre-commit "cd frontend && npm run precommit"
   ```

## Development Workflow

### Code Quality Tools

- **ESLint**: Linting and code quality rules
- **Prettier**: Code formatting
- **TypeScript**: Type checking
- **Husky**: Git hooks
- **Lint-staged**: Run linters on staged files

### Available Scripts

```bash
# Development
npm run dev              # Start development server with Turbopack
npm run build           # Build for production
npm run start           # Start production server

# Code Quality
npm run lint            # Run ESLint
npm run lint:fix        # Run ESLint with auto-fix
npm run format          # Format all files with Prettier
npm run format:check    # Check if files are formatted
npm run type-check      # Run TypeScript type checking

# Git Hooks
npm run precommit       # Run lint-staged (used by Husky)
```

### IDE Setup (VS Code)

The project includes VS Code configuration:

- **Recommended Extensions**: Automatically suggested when opening the project
- **Settings**: Pre-configured for optimal development experience
- **Format on Save**: Enabled with Prettier
- **ESLint Integration**: Real-time linting feedback

### Code Style Guidelines

#### TypeScript
- Use TypeScript for all new files
- Enable strict mode
- Prefer explicit return types for functions
- Use meaningful variable names

#### React/Next.js
- Use functional components with hooks
- Prefer arrow functions for components
- Use TypeScript interfaces for props
- Follow Next.js 14 App Router patterns

#### Imports
- Group imports: React/Next.js → Third-party → Local
- Use absolute imports with `@/` prefix
- Sort imports alphabetically within groups

#### Styling
- Use Tailwind CSS for styling
- Use `cn()` utility for conditional classes
- Follow mobile-first responsive design
- Use semantic HTML elements

#### File Naming
- Components: PascalCase (`UserProfile.tsx`)
- Hooks: camelCase with `use` prefix (`useAuth.ts`)
- Utilities: camelCase (`formatDate.ts`)
- Pages: kebab-case in app directory

### Git Workflow

1. **Before committing:**
   - ESLint runs and fixes issues
   - Prettier formats code
   - TypeScript checks for errors

2. **Commit messages:**
   - Use conventional commits format
   - Examples:
     - `feat: add user authentication`
     - `fix: resolve environment variable issue`
     - `docs: update setup instructions`

3. **Pre-commit hooks:**
   - Only staged files are linted and formatted
   - Commit is blocked if linting fails
   - Type checking ensures no TypeScript errors

### Debugging

#### VS Code Debugging
- Use built-in debugger for server-side code
- Browser DevTools for client-side debugging
- Error Lens extension for inline error display

#### Common Issues
- **ESLint errors**: Run `npm run lint:fix`
- **Prettier conflicts**: Run `npm run format`
- **Type errors**: Run `npm run type-check`
- **Environment issues**: Check `/health` endpoint

### Performance

#### Development
- Turbopack enabled for faster builds
- Hot reload for instant feedback
- TypeScript incremental compilation

#### Build Optimization
- Bundle analysis available
- Tree shaking enabled
- Image optimization configured
- Static generation where possible

### Testing (Future)

When tests are added:
- Jest for unit tests
- React Testing Library for component tests
- Playwright for E2E tests
- Coverage reports generated

## Troubleshooting

### Common Setup Issues

1. **Node version incompatibility:**
   ```bash
   node --version  # Should be 18+
   ```

2. **Package installation fails:**
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **ESLint/Prettier conflicts:**
   - Check `.eslintrc.js` and `.prettierrc` configuration
   - Restart VS Code
   - Run `npm run lint:fix && npm run format`

4. **Git hooks not working:**
   ```bash
   # From parent directory
   npx husky install
   chmod +x .husky/pre-commit
   ```

### Getting Help

- Check error messages in VS Code Problems panel
- Use `/health` endpoint to verify configuration
- Review environment setup in `ENVIRONMENT_SETUP.md`
- Consult Next.js and React documentation

## Best Practices

1. **Always run development server locally before committing**
2. **Test your changes thoroughly**
3. **Keep commits small and focused**
4. **Write meaningful commit messages**
5. **Use TypeScript strictly**
6. **Follow established patterns in the codebase**
7. **Update documentation when needed**