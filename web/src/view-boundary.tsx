import { Component, type ReactNode } from 'react';

/** A failed lazy chunk or view must not erase the whole research workspace. */
export class ViewBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <section className="notice error" role="alert"><h2>This view could not be opened.</h2><p>The application may have been rebuilt while this tab was open. Drafts and saved snapshots remain in browser storage. Reload to use the current build.</p><button className="button" onClick={() => location.reload()}>Reload the studio</button></section>;
    return this.props.children;
  }
}
