// Hub Footer: single card-like button linking back to main site
import './HubFooter.css';

export function HubFooter() {
  return (
    <footer className="chrislawrence-footer">
      <div className="container text-center">
        <a
          href="https://chrislawrence.ca"
          className="hub-home-btn"
          aria-label="Visit main site chrislawrence.ca to view all projects"
        >
          <span className="hub-home-text">Visit main site: chrislawrence.ca</span>
        </a>
      </div>
    </footer>
  );
}

export default HubFooter;


