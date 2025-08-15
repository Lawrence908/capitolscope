import React from 'react';
import { Link } from 'react-router-dom';
import DarkModeToggle from './DarkModeToggle';

const PrivacyPolicy: React.FC = () => {
  return (
    <div className="min-h-screen bg-bg-light-primary dark:bg-bg-primary">
      {/* Header */}
      <header className="bg-bg-light-secondary dark:bg-bg-secondary shadow-lg border-b border-primary-800/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4 sm:py-6">
            <Link to="/dashboard" className="flex items-center">
              <img 
                src="/capitol-scope-logo.png" 
                alt="CapitolScope Logo" 
                className="h-10 w-10 rounded-lg shadow-glow-primary/20"
                loading="lazy"
                width="40"
                height="40"
              />
              <h1 className="ml-3 text-lg sm:text-xl font-bold text-glow-primary">CapitolScope</h1>
            </Link>
            <div className="flex items-center gap-4">
              <DarkModeToggle />
              <Link
                to="/dashboard"
                className="text-sm sm:text-base text-neutral-700 dark:text-neutral-300 hover:text-primary-400 transition-colors duration-300"
              >
                ← Back to Dashboard
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        <div className="card p-8">
          <h1 className="text-3xl sm:text-4xl font-bold text-primary-600 dark:text-glow-primary mb-8">
            Privacy Policy
          </h1>
          
          <div className="prose prose-neutral dark:prose-invert max-w-none">
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-8">
              <strong>Last updated:</strong> August 15, 2025
            </p>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                1. Introduction
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                CapitolScope ("we," "our," or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our congressional trading transparency platform.
              </p>
              <p className="text-neutral-700 dark:text-neutral-300">
                By using CapitolScope, you agree to the collection and use of information in accordance with this policy.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                2. Information We Collect
              </h2>
              
              <h3 className="text-xl font-medium text-neutral-900 dark:text-neutral-100 mb-3">
                2.1 Personal Information
              </h3>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li><strong>Account Information:</strong> Email address, password, name, and subscription preferences</li>
                <li><strong>Profile Data:</strong> User preferences, notification settings, and account activity</li>
                <li><strong>Payment Information:</strong> Billing details processed securely through Stripe (we do not store credit card information)</li>
                <li><strong>Communication Data:</strong> Support requests, feedback, and email communications</li>
              </ul>

              <h3 className="text-xl font-medium text-neutral-900 dark:text-neutral-100 mb-3">
                2.2 Usage Information
              </h3>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li><strong>Platform Usage:</strong> Pages visited, features used, and interaction patterns</li>
                <li><strong>Technical Data:</strong> IP address, browser type, device information, and access timestamps</li>
                <li><strong>Analytics Data:</strong> Performance metrics, error logs, and user behavior analytics</li>
              </ul>

              <h3 className="text-xl font-medium text-neutral-900 dark:text-neutral-100 mb-3">
                2.3 Public Data
              </h3>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                We collect and process publicly available congressional trading data from official sources including:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li>Congress.gov API for official trading disclosures</li>
                <li>Public financial data from Yahoo Finance, Alpha Vantage, and Polygon.io</li>
                <li>Publicly available congressional member information</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                3. How We Use Your Information
              </h2>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li><strong>Service Provision:</strong> To provide and maintain our congressional trading transparency platform</li>
                <li><strong>Account Management:</strong> To manage your account, process payments, and provide customer support</li>
                <li><strong>Personalization:</strong> To customize your experience and provide relevant content and features</li>
                <li><strong>Communication:</strong> To send important updates, notifications, and marketing communications (with your consent)</li>
                <li><strong>Analytics:</strong> To analyze usage patterns and improve our platform</li>
                <li><strong>Security:</strong> To protect against fraud, abuse, and security threats</li>
                <li><strong>Legal Compliance:</strong> To comply with applicable laws and regulations</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                4. Information Sharing and Disclosure
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                We do not sell, trade, or rent your personal information to third parties. We may share your information in the following circumstances:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li><strong>Service Providers:</strong> With trusted third-party service providers who assist in operating our platform (payment processing, email services, analytics)</li>
                <li><strong>Legal Requirements:</strong> When required by law, court order, or government request</li>
                <li><strong>Business Transfers:</strong> In connection with a merger, acquisition, or sale of assets</li>
                <li><strong>Safety and Security:</strong> To protect our rights, property, or safety, or that of our users</li>
                <li><strong>Consent:</strong> With your explicit consent for specific purposes</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                5. Data Security
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                We implement comprehensive security measures to protect your information:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li><strong>Encryption:</strong> All data is encrypted in transit and at rest using industry-standard protocols</li>
                <li><strong>Access Controls:</strong> Strict access controls and authentication mechanisms</li>
                <li><strong>Regular Audits:</strong> Regular security assessments and vulnerability testing</li>
                <li><strong>Secure Infrastructure:</strong> Cloud-based infrastructure with enterprise-grade security</li>
                <li><strong>Employee Training:</strong> Regular security training for all team members</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                6. Data Retention
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                We retain your information for as long as necessary to provide our services and comply with legal obligations:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li><strong>Account Data:</strong> Retained while your account is active and for a reasonable period after deletion</li>
                <li><strong>Usage Data:</strong> Retained for analytics and service improvement purposes</li>
                <li><strong>Financial Records:</strong> Retained as required by law and accounting standards</li>
                <li><strong>Public Data:</strong> Congressional trading data is retained indefinitely as it is public information</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                7. Your Rights and Choices
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                You have the following rights regarding your personal information:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li><strong>Access:</strong> Request access to your personal information</li>
                <li><strong>Correction:</strong> Request correction of inaccurate information</li>
                <li><strong>Deletion:</strong> Request deletion of your personal information</li>
                <li><strong>Portability:</strong> Request a copy of your data in a portable format</li>
                <li><strong>Opt-out:</strong> Opt out of marketing communications</li>
                <li><strong>Account Settings:</strong> Update your preferences through your account settings</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                8. Cookies and Tracking Technologies
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                We use cookies and similar technologies to enhance your experience:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li><strong>Essential Cookies:</strong> Required for basic platform functionality</li>
                <li><strong>Analytics Cookies:</strong> Help us understand how you use our platform</li>
                <li><strong>Preference Cookies:</strong> Remember your settings and preferences</li>
                <li><strong>Security Cookies:</strong> Help protect against fraud and abuse</li>
              </ul>
              <p className="text-neutral-700 dark:text-neutral-300">
                You can control cookie settings through your browser preferences.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                9. Third-Party Services
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                Our platform integrates with third-party services:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li><strong>Stripe:</strong> Payment processing (subject to Stripe's privacy policy)</li>
                <li><strong>SendGrid:</strong> Email delivery services</li>
                <li><strong>Google Analytics:</strong> Website analytics and performance monitoring</li>
                <li><strong>Financial Data APIs:</strong> Yahoo Finance, Alpha Vantage, Polygon.io for market data</li>
              </ul>
              <p className="text-neutral-700 dark:text-neutral-300">
                These services have their own privacy policies, and we encourage you to review them.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                10. Children's Privacy
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300">
                CapitolScope is not intended for children under 13 years of age. We do not knowingly collect personal information from children under 13. If you believe we have collected information from a child under 13, please contact us immediately.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                11. International Data Transfers
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300">
                Your information may be transferred to and processed in countries other than your own. We ensure appropriate safeguards are in place to protect your information in accordance with this Privacy Policy and applicable data protection laws.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                12. Changes to This Privacy Policy
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                We may update this Privacy Policy from time to time. We will notify you of any material changes by:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li>Posting the updated policy on our platform</li>
                <li>Sending you an email notification</li>
                <li>Displaying a prominent notice on our website</li>
              </ul>
              <p className="text-neutral-700 dark:text-neutral-300">
                Your continued use of CapitolScope after any changes constitutes acceptance of the updated policy.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                13. Contact Us
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                If you have any questions about this Privacy Policy or our data practices, please contact us:
              </p>
              <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
                <p className="text-neutral-700 dark:text-neutral-300">
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
