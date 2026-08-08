import React from "react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: (error: Error, reset: () => void) => React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * App-level error boundary. Wraps the main render tree so a single
 * component throwing does not take down the whole page.
 *
 * Behaviour:
 *   - In dev: shows the raw error + stack, with a "Reload" button.
 *   - In prod: shows a calm "Something went wrong" message + a reload
 *     button and a WhatsApp-deep-link to the founder, so a user who
 *     hit a runtime error has a one-tap path to support.
 *
 * Note: an error boundary does NOT catch errors in event handlers
 * (use a try/catch in the handler) or in async code (use .catch()
 * or try/await). It catches errors during render and in lifecycle
 * methods.
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    // Centralised log point. Wire to Sentry / Axiom / Logflare here when
    // a monitoring backend is selected (deferred to S7).
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary] caught", error, info);
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  private handleReload = (): void => {
    if (typeof window !== "undefined") {
      window.location.reload();
    }
  };

  render(): React.ReactNode {
    if (!this.state.hasError || !this.state.error) {
      return this.props.children;
    }

    if (this.props.fallback) {
      return this.props.fallback(this.state.error, this.handleReset);
    }

    const isDev = typeof import.meta !== "undefined" && import.meta.env?.DEV;

    return (
      <div
        className="min-h-screen flex items-center justify-center px-4 py-16"
        style={{ backgroundColor: "#030810" }}
      >
        <div className="max-w-xl w-full text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-500/10 border border-red-500/30 text-red-400 text-2xl font-bold mb-6">
            !
          </div>
          <h1 className="text-2xl font-bold text-white mb-3">
            Something broke boss.
          </h1>
          <p className="text-gray-400 mb-8 leading-relaxed">
            The page hit a runtime error. Reload usually fixes it. If it keeps happening, drop us a line on WhatsApp and we&apos;ll jump on it.
          </p>

          {isDev && this.state.error && (
            <pre className="text-left text-xs text-red-300 bg-red-500/5 border border-red-500/20 rounded-lg p-4 mb-6 overflow-x-auto max-h-64">
              {this.state.error.name}: {this.state.error.message}
              {"\n\n"}
              {this.state.error.stack}
            </pre>
          )}

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              type="button"
              onClick={this.handleReload}
              className="px-6 py-3 rounded-xl font-semibold bg-gradient-to-r from-emerald-500 to-emerald-400 text-dark-900 shadow-[0_0_20px_rgba(16,185,129,0.4)] hover:shadow-[0_0_30px_rgba(16,185,129,0.6)] transition-all"
            >
              Reload page
            </button>
            <a
              href="https://wa.me/60174106981?text=Hi%2C%20the%20Bijou%20AI%20landing%20page%20hit%20an%20error.%20Can%20you%20take%20a%20look%3F"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 rounded-xl font-semibold glass-panel-3d text-white border border-white/10 hover:border-emerald-400/40 transition-all"
            >
              Report on WhatsApp
            </a>
          </div>
        </div>
      </div>
    );
  }
}
