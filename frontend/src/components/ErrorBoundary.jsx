import React from "react";

import { reportError } from "../utils/errorReporting";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    reportError(error, {
      source: "react-error-boundary",
      componentStack: errorInfo?.componentStack,
    });
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <main className="app-error-boundary" role="alert">
        <section>
          <p className="eyebrow">Something broke</p>
          <h1>AgentNexLiFy hit an unexpected UI error.</h1>
          <p>
            Reload the page once. If it keeps happening, check the browser console
            and production logs with the current URL and user action.
          </p>
          <button type="button" onClick={() => window.location.reload()}>
            Reload page
          </button>
        </section>
      </main>
    );
  }
}
