# Contributing to Bijou AI

First off, thanks for taking the time to contribute! 🎉

The following is a set of guidelines for contributing to Bijou AI. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## Code of Conduct

This project and everyone participating in it is governed by a Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

*   **Use a clear and descriptive title** for the issue to identify the problem.
*   **Describe the exact steps to reproduce the problem** in as many details as possible.
*   **Provide specific examples** to demonstrate the steps.

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion, including completely new features and minor improvements to existing functionality.

*   **Use a clear and descriptive title** for the issue.
*   **Provide a step-by-step description of the suggested enhancement** in as many details as possible.
*   **Explain why this enhancement would be useful** to most Bijou AI users.

### Pull Requests

1.  Fork the repo and create your branch from `main`.
2.  If you've added code that should be tested, add tests.
3.  Ensure the test suite passes.
4.  Make sure your code lints.
5.  Issue that pull request!

## Styleguides

### Git Commit Messages

*   Use the present tense ("Add feature" not "Added feature").
*   Use the imperative mood ("Move cursor to..." not "Moves cursor to...").
*   Limit the first line to 72 characters or less.
*   Reference issues and pull requests liberally after the first line.

### JavaScript/TypeScript Style

*   We use **TypeScript** for type safety. Please ensure all new components and functions are typed.
*   We use **Prettier** for code formatting.
*   **Tailwind CSS** is used for styling. Avoid inline styles where possible.
*   **Functional Components** with Hooks are preferred over Class Components.

## Development Workflow

1.  **Mocking AI calls:** If you do not have an API key, the `services/gemini.ts` file has a fallback mechanism. You can also extend the `ToolOrchestrator` in `services/tools.ts` to mock more complex backend interactions without a real server.

2.  **Animations:** We use `framer-motion`. Please respect the user's `prefers-reduced-motion` settings where applicable (though this is a high-fidelity demo, accessibility is still important).

Thank you for contributing!
