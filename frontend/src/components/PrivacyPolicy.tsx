import React from 'react';
import { Link } from 'react-router-dom';
import DarkModeToggle from './DarkModeToggle';

const PrivacyPolicy: React.FC = () => {
  return (
    <div className="min-h-screen bg-surface">
      {/* Header */}
      <header className="bg-slab text-slab-on">
        <div className="mx-auto flex h-[68px] max-w-[1320px] items-center justify-between px-4 sm:px-8">
          <Link to="/" className="flex shrink-0 items-center gap-2.5" aria-label="CapitolScope home">
            <span aria-hidden="true" className="block h-9 w-1.5 bg-accent" />
            <span className="font-display text-[21px] font-extrabold leading-[0.82] tracking-[0.02em] text-slab-on">
              CAPITOL
              <br />
              SCOPE
            </span>
          </Link>
          <div className="flex items-center gap-4">
            <DarkModeToggle />
            <Link
              to="/dashboard"
              className="font-ui text-sm font-semibold text-slab-muted transition-colors hover:text-slab-on"
            >
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        <div>
          <h1 className="mb-6 border-b-[3px] border-content pb-6 font-display text-6xl font-extrabold leading-[0.9] text-content sm:text-7xl">
            Privacy Policy
          </h1>
          
          <div className="max-w-none font-ui text-[15px] leading-relaxed">
            <p className="mb-8 text-sm text-content-faint">
              <strong>Last updated:</strong> August 15, 2025
            </p>

            <section className="mb-10">
              <h2 className="mb-4 border-t-[3px] border-content pt-3 font-display text-3xl font-extrabold leading-none text-content">
                1. Introduction
              </h2>
              <p className="text-content-muted mb-4">
                CapitolScope ("we," "our," or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our congressional trading transparency platform.
              </p>
              <p className="text-content-muted">
                By using CapitolScope, you agree to the collection and use of information in accordance with this policy.
              </p>
            </section>

            <section className="mb-10">
              <h2 className="mb-4 border-t-[3px] border-content pt-3 font-display text-3xl font-extrabold leading-none text-content">
                2. Information We Collect
              </h2>
              
              <h3 className="mb-2 mt-5 font-ui text-base font-bold text-content">
                2.1 Personal Information
              </h3>
              <ul className="list-disc pl-6 mb-4 text-content-muted">
                <li><strong>Account Information:</strong> Email address, password, name, and subscription preferences</li>
                <li><strong>Profile Data:</strong> User preferences, notification settings, and account activity</li>
                <li><strong>Payment Information:</strong> Billing details processed securely through Stripe (we do not store credit card information)</li>
                <li><strong>Communication Data:</strong> Support requests, feedback, and email communications</li>
              </ul>

              <h3 className="mb-2 mt-5 font-ui text-base font-bold text-content">
                2.2 Usage Information
              </h3>
              <ul className="list-disc pl-6 mb-4 text-content-muted">
                <li><strong>Platform Usage:</strong> Pages visited, features used, and interaction patterns</li>
                <li><strong>Technical Data:</strong> IP address, browser type, device information, and access timestamps</li>
                <li><strong>Analytics Data:</strong> Performance metrics, error logs, and user behavior analytics</li>
              </ul>

              <h3 className="mb-2 mt-5 font-ui text-base font-bold text-content">
                2.3 Public Data
              </h3>
              <p className="text-content-muted mb-4">
                We collect and process publicly available congressional trading data from official sources including:
              </p>
              <ul className="list-disc pl-6 mb-4 text-content-muted">
                <li>Congress.gov API for official trading disclosures</li>
                <li>Public financial data from Yahoo Finance, Alpha Vantage, and Polygon.io</li>
                <li>Publicly available congressional member information</li>
              </ul>
            </section>

            <section className="mb-10">
              <h2 className="mb-4 border-t-[3px] border-content pt-3 font-display text-3xl font-extrabold leading-none text-content">
                3. How We Use Your Information
              </h2>
              <ul className="list-disc pl-6 mb-4 text-content-muted">
                <li><strong>Service Provision:</strong> To provide and maintain our congressional trading transparency platform</li>
                <li><strong>Account Management:</strong> To manage your account, process payments, and provide customer support</li>
                <li><strong>Personalization:</strong> To customize your experience and provide relevant content and features</li>
                <li><strong>Communication:</strong> To send important updates, notifications, and marketing communications (with your consent)</li>
                <li><strong>Analytics:</strong> To analyze usage patterns and improve our platform</li>
                <li><strong>Security:</strong> To protect against fraud, abuse, and security threats</li>
                <li><strong>Legal Compliance:</strong> To comply with applicable laws and regulations</li>
              </ul>
            </section>

            <section className="mb-10">
              <h2 className="mb-4 border-t-[3px] border-content pt-3 font-display text-3xl font-extrabold leading-none text-content">
                4. Information Sharing and Disclosure
              </h2>
              <p className="text-content-muted mb-4">
                We do not sell, trade, or rent your personal information to third parties. We may share your information in the following circumstances:
              </p>
              <ul className="list-disc pl-6 mb-4 text-content-muted">
                <li><strong>Service Providers:</strong> With trusted third-party service providers who assist in operating our platform (payment processing, email services, analytics)</li>
                <li><strong>Legal Requirements:</strong> When required by law, court order, or government request</li>
                <li><strong>Business Transfers:</strong> In connection with a merger, acquisition, or sale of assets</li>
                <li><strong>Safety and Security:</strong> To protect our rights, property, or safety, or that of our users</li>
                <li><strong>Consent:</strong> With your explicit consent for specific purposes</li>
              </ul>
            </section>

            <section className="mb-10">
              <h2 className="mb-4 border-t-[3px] border-content pt-3 font-display text-3xl font-extrabold leading-none text-content">
                5. Data Security
              </h2>
              <p className="text-content-muted mb-4">
                We implement comprehensive security measures to protect your information:
              </p>
              <ul className="list-disc pl-6 mb-4 text-content-muted">
                <li><strong>Encryption:</strong> All data is encrypted in transit and at rest using industry-standard protocols</li>
                <li><strong>Access Controls:</strong> Strict access controls and authentication mechanisms</li>
                <li><strong>Regular Audits:</strong> Regular security assessments and vulnerability testing</li>
                <li><strong>Secure Infrastructure:</strong> Cloud-based infrastructure with enterprise-grade security</li>
                <li><strong>Employee Training:</strong> Regular security training for all team members</li>
              </ul>
            </section>

            <section className="mb-10">
              <h2 className="mb-4 border-t-[3px] border-content pt-3 font-display text-3xl font-extrabold leading-none text-content">
                6. Data Retention
              </h2>
              <p className="text-content-muted mb-4">
                We retain your information for as long as necessary to provide our services and comply with legal obligations:
              </p>
              <ul className="list-disc pl-6 mb-4 text-content-muted">
                <li><strong>Account Data:</strong> Retained while your account is active and for a reasonable period after deletion</li>
                <li><strong>Usage Data:</strong> Retained for analytics and service improvement purposes</li>
                <li><strong>Financial Records:</strong> Retained as required by law and accounting standards</li>
                <li><strong>Public Data:</strong> Congressional trading data is retained indefinitely as it is public information</li>
              </ul>
            </section>

            <section className="mb-10">
              <h2 className="mb-4 border-t-[3px] border-content pt-3 font-display text-3xl font-extrabold leading-none text-content">
                7. Your Rights and Choices
              </h2>
              <p className="text-content-muted mb-4">
                You have the following rights regarding your personal information:
              </p>
              <ul className="list-disc pl-6 mb-4 text-content-muted">
                <li><strong>Access:</strong> Request access to your personal information</li>
                <li><strong>Correction:</strong> Request correction of inaccurate information</li>
                <li><strong>Deletion:</strong> Request deletion of your personal information</li>
                <li><strong>Portability:</strong> Request a copy of your data in a portable format</li>
                <li><strong>Opt-out:</strong> Opt out of marketing communications</li>
                <li><strong>Account Settings:</strong> Update your preferences through your account settings</li>
              </ul>
            </section>

            <section className="mb-10">
              <h2 className="mb-4 border-t-[3px] border-content pt-3 font-display text-3xl font-extrabold leading-none text-content">
                8. Cookies and Tracking Technologies
              </h2>
              <p className="text-content-muted mb-4">
                We use cookies and similar technologies to enhance your experience:
              </p>
              <ul className="list-disc pl-6 mb-4 text-content-muted">
                <li><strong>Essential Cookies:</strong> Required for basic platform functionality</li>
                <li><strong>Analytics Cookies:</strong> Help us understand how you use our platform</li>
                <li><strong>Preference Cookies:</strong> Remember your settings and preferences</li>
                <li><strong>Security Cookies:</strong> Help protect against fraud and abuse</li>
              </ul>
              <p className="text-content-muted">
                You can control cookie settings through your browser preferences.
              </p>
            </section>

            <section className="mb-10">
              <h2 className="mb-4 border-t-[3px] border-content pt-3 font-display text-3xl font-extrabold leading-none text-content">
                9. Third-Party Services
              </h2>
              <p className="text-content-muted mb-4">
                Our platform integrates with third-party services:
              </p>
              <ul className="list-disc pl-6 mb-4 text-content-muted">
                <li><strong>Stripe:</strong> Payment processing (subject to Stripe's privacy policy)</li>
                <li><strong>SendGrid:</strong> Email delivery services</li>
                <li><strong>Google Analytics:</strong> Website analytics and performance monitoring</li>
                <li><strong>Financial Data APIs:</strong> Yahoo Finance, Alpha Vantage, Polygon.io for market data</li>
              </ul>
              <p className="text-content-muted">
                These services have their own privacy policies, and we encourage you to review them.
              </p>
            </section>

            <section className="mb-10">
              <h2 className="mb-4 border-t-[3px] border-content pt-3 font-display text-3xl font-extrabold leading-none text-content">
                10. Children's Privacy
              </h2>
              <p className="text-content-muted">
                CapitolScope is not intended for children under 13 years of age. We do not knowingly collect personal information from children under 13. If you believe we have collected information from a child under 13, please contact us immediately.
              </p>
            </section>

            <section className="mb-10">
              <h2 className="mb-4 border-t-[3px] border-content pt-3 font-display text-3xl font-extrabold leading-none text-content">
                11. International Data Transfers
              </h2>
              <p className="text-content-muted">
                Your information may be transferred to and processed in countries other than your own. We ensure appropriate safeguards are in place to protect your information in accordance with this Privacy Policy and applicable data protection laws.
              </p>
            </section>

            <section className="mb-10">
              <h2 className="mb-4 border-t-[3px] border-content pt-3 font-display text-3xl font-extrabold leading-none text-content">
                12. Changes to This Privacy Policy
              </h2>
              <p className="text-content-muted mb-4">
                We may update this Privacy Policy from time to time. We will notify you of any material changes by:
              </p>
              <ul className="list-disc pl-6 mb-4 text-content-muted">
                <li>Posting the updated policy on our platform</li>
                <li>Sending you an email notification</li>
                <li>Displaying a prominent notice on our website</li>
              </ul>
              <p className="text-content-muted">
                Your continued use of CapitolScope after any changes constitutes acceptance of the updated policy.
              </p>
            </section>

            <section className="mb-10">
              <h2 className="mb-4 border-t-[3px] border-content pt-3 font-display text-3xl font-extrabold leading-none text-content">
                13. Contact Us
              </h2>
              <p className="text-content-muted mb-4">
                If you have any questions about this Privacy Policy or our data practices, please contact us:
              </p>
              <div className="border-l-4 border-content bg-surface-inset p-4">
                <p className="text-content-muted">
                  <strong>Email:</strong> capitolscope@gmail.com<br />
                  <strong>Address:</strong> CapitolScope Privacy Team<br />
                  <strong>Website:</strong> https://capitolscope.chrislawrence.ca/
                </p>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
};

export default PrivacyPolicy;
