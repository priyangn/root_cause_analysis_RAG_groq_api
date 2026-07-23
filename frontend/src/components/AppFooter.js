import React from 'react';

const YEAR = new Date().getFullYear();

export default function AppFooter() {
  return (
    <footer
      className="border-t border-border bg-card/60 mt-auto"
      data-testid="app-footer"
    >
      <div className="max-w-5xl mx-auto px-6 py-5 text-center space-y-2">
        <p className="text-xs text-muted-foreground">
          © {YEAR} CauseSense AI. All rights reserved.
        </p>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Made with AI · For research and educational purposes only.
          AI-generated analyses and recommendations may be incomplete or misleading
          and are not a substitute for professional engineering judgment.
          Always validate results with qualified experts before taking operational action.
        </p>
      </div>
    </footer>
  );
}
