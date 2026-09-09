// Shared hub footer. Markup mirrors the canonical block in
// daedalus-infra/proxy/shared-footer/footer.html and is styled solely by
// /shared-footer/footer.css, linked from index.html. Do not style it locally:
// a local copy forks the shared component and drifts.
export function HubFooter() {
  return (
    <footer className="chrislawrence-footer">
      <a href="https://chrislawrence.ca" className="footer-home-link" aria-label="Back to chrislawrence.ca">
        <img
          src="/shared-footer/logo-portrait.png"
          alt="Chris Lawrence"
          className="footer-logo"
          width={32}
          height={32}
          loading="lazy"
          onError={(e) => e.currentTarget.remove()}
        />
        <span className="footer-home-link-text">Back to chrislawrence.ca</span>
      </a>
    </footer>
  );
}

export default HubFooter;
