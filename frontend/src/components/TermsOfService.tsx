import React from 'react';
import { Link } from 'react-router-dom';
import DarkModeToggle from './DarkModeToggle';

const TermsOfService: React.FC = () => {
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
            Terms of Service
          </h1>
          
          <div className="prose prose-neutral dark:prose-invert max-w-none">
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-8">
              <strong>Last updated:</strong> August 15, 2025
            </p>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                1. Acceptance of Terms
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                By accessing and using CapitolScope ("the Service"), you accept and agree to be bound by the terms and provision of this agreement. If you do not agree to abide by the above, please do not use this service.
              </p>
              <p className="text-neutral-700 dark:text-neutral-300">
                CapitolScope is a congressional trading transparency platform that provides access to publicly available trading data and analytics tools.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                2. Description of Service
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                CapitolScope provides:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li>Access to congressional trading data from official sources</li>
                <li>Portfolio analytics and performance tracking tools</li>
                <li>Real-time alerts and notifications</li>
                <li>Data export and API access (for premium tiers)</li>
                <li>Interactive charts and visualization tools</li>
                <li>Community features and discussion forums</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                3. User Accounts and Registration
              </h2>
              <h3 className="text-xl font-medium text-neutral-900 dark:text-neutral-100 mb-3">
                3.1 Account Creation
              </h3>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                To access certain features of CapitolScope, you must create an account. You agree to:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li>Provide accurate, current, and complete information</li>
                <li>Maintain and update your account information</li>
                <li>Keep your password secure and confidential</li>
                <li>Accept responsibility for all activities under your account</li>
                <li>Notify us immediately of any unauthorized use</li>
              </ul>

              <h3 className="text-xl font-medium text-neutral-900 dark:text-neutral-100 mb-3">
                3.2 Account Termination
              </h3>
              <p className="text-neutral-700 dark:text-neutral-300">
                We reserve the right to terminate or suspend your account at any time for violations of these terms or for any other reason at our sole discretion.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                4. Subscription Terms
              </h2>
              <h3 className="text-xl font-medium text-neutral-900 dark:text-neutral-100 mb-3">
                4.1 Subscription Tiers
              </h3>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                CapitolScope offers multiple subscription tiers:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li><strong>Free Tier:</strong> Basic access with limited features</li>
                <li><strong>Pro Tier:</strong> $5.99/month - Enhanced features and data access</li>
                <li><strong>Premium Tier:</strong> $14.99/month - Full platform access including API</li>
                <li><strong>Enterprise Tier:</strong> Custom pricing for organizations</li>
              </ul>

              <h3 className="text-xl font-medium text-neutral-900 dark:text-neutral-100 mb-3">
                4.2 Billing and Payment
              </h3>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li>Subscriptions are billed in advance on a recurring basis</li>
                <li>Payments are processed securely through Stripe</li>
                <li>All fees are non-refundable except as required by law</li>
                <li>We may change subscription prices with 30 days notice</li>
                <li>Failed payments may result in service suspension</li>
              </ul>

              <h3 className="text-xl font-medium text-neutral-900 dark:text-neutral-100 mb-3">
                4.3 Cancellation
              </h3>
              <p className="text-neutral-700 dark:text-neutral-300">
                You may cancel your subscription at any time through your account settings. You will continue to have access until the end of your current billing period.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                5. Acceptable Use Policy
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                You agree not to use the Service to:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li>Violate any applicable laws or regulations</li>
                <li>Infringe on intellectual property rights</li>
                <li>Transmit harmful, offensive, or inappropriate content</li>
                <li>Attempt to gain unauthorized access to our systems</li>
                <li>Interfere with or disrupt the Service</li>
                <li>Use automated tools to access the Service excessively</li>
                <li>Share account credentials with others</li>
                <li>Use the Service for commercial purposes without authorization</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                6. Data and Content
              </h2>
              <h3 className="text-xl font-medium text-neutral-900 dark:text-neutral-100 mb-3">
                6.1 Data Sources
              </h3>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                CapitolScope aggregates data from multiple sources:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li>Congress.gov API for official trading disclosures</li>
                <li>Yahoo Finance, Alpha Vantage, and Polygon.io for market data</li>
                <li>Public congressional member information</li>
                <li>User-generated content and portfolios</li>
              </ul>

              <h3 className="text-xl font-medium text-neutral-900 dark:text-neutral-100 mb-3">
                6.2 Data Accuracy
              </h3>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                While we strive for accuracy, we cannot guarantee:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li>Completeness of all trading data</li>
                <li>Real-time accuracy of market prices</li>
                <li>Error-free data processing</li>
                <li>Availability of all historical data</li>
              </ul>

              <h3 className="text-xl font-medium text-neutral-900 dark:text-neutral-100 mb-3">
                6.3 User Content
              </h3>
              <p className="text-neutral-700 dark:text-neutral-300">
                You retain ownership of content you create. By posting content, you grant us a license to use, display, and distribute it in connection with the Service.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                7. Intellectual Property
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                CapitolScope and its original content, features, and functionality are owned by CapitolScope and are protected by international copyright, trademark, patent, trade secret, and other intellectual property laws.
              </p>
              <p className="text-neutral-700 dark:text-neutral-300">
                You may not reproduce, distribute, modify, or create derivative works of our content without express written permission.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                8. Privacy and Data Protection
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                Your privacy is important to us. Our collection and use of personal information is governed by our Privacy Policy, which is incorporated into these Terms by reference.
              </p>
              <p className="text-neutral-700 dark:text-neutral-300">
                By using CapitolScope, you consent to the collection and use of information as described in our Privacy Policy.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                9. Disclaimers and Limitations
              </h2>
              <h3 className="text-xl font-medium text-neutral-900 dark:text-neutral-100 mb-3">
                9.1 Service Availability
              </h3>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                We strive to maintain high availability but cannot guarantee uninterrupted access. The Service may be temporarily unavailable due to maintenance, updates, or technical issues.
              </p>

              <h3 className="text-xl font-medium text-neutral-900 dark:text-neutral-100 mb-3">
                9.2 Investment Disclaimer
              </h3>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                <strong>IMPORTANT:</strong> CapitolScope is for informational purposes only. We do not provide investment advice, and the information provided should not be considered as such. Always consult with qualified financial advisors before making investment decisions.
              </p>

              <h3 className="text-xl font-medium text-neutral-900 dark:text-neutral-100 mb-3">
                9.3 Limitation of Liability
              </h3>
              <p className="text-neutral-700 dark:text-neutral-300">
                To the maximum extent permitted by law, CapitolScope shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including but not limited to loss of profits, data, or use.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                10. Indemnification
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300">
                You agree to indemnify and hold harmless CapitolScope, its officers, directors, employees, and agents from any claims, damages, or expenses arising from your use of the Service or violation of these Terms.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                11. Governing Law and Dispute Resolution
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                These Terms shall be governed by and construed in accordance with the laws of the jurisdiction in which CapitolScope operates, without regard to conflict of law principles.
              </p>
              <p className="text-neutral-700 dark:text-neutral-300">
                Any disputes arising from these Terms or your use of the Service shall be resolved through binding arbitration in accordance with the rules of the American Arbitration Association.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                12. Changes to Terms
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                We reserve the right to modify these Terms at any time. We will notify users of material changes by:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300">
                <li>Posting the updated Terms on our platform</li>
                <li>Sending email notifications to registered users</li>
                <li>Displaying prominent notices on our website</li>
              </ul>
              <p className="text-neutral-700 dark:text-neutral-300">
                Your continued use of CapitolScope after changes constitutes acceptance of the updated Terms.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                13. Severability
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300">
                If any provision of these Terms is found to be unenforceable or invalid, that provision will be limited or eliminated to the minimum extent necessary so that the Terms will otherwise remain in full force and effect.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                14. Entire Agreement
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300">
                These Terms, together with our Privacy Policy, constitute the entire agreement between you and CapitolScope regarding the use of the Service.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-primary-500 dark:text-primary-400 mb-4">
                15. Contact Information
              </h2>
              <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                If you have any questions about these Terms of Service, please contact us:
              </p>
              <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
                <p className="text-neutral-700 dark:text-neutral-300">
                  <strong>Email:</strong> capitolscope@gmail.com<br />
                  <strong>Address:</strong> CapitolScope Legal Team<br />
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

export default TermsOfService;
