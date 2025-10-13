#!/usr/bin/env python3
"""
Stripe Products Setup Script for CapitolScope

This script creates the necessary Stripe products and pricing plans
for the CapitolScope subscription tiers (Pro, Premium, Enterprise)
with both monthly and yearly billing cycles.

Usage:
    python scripts/setup_stripe_products.py

Requirements:
    - Stripe Python SDK installed
    - Valid Stripe secret key in environment
    - Stripe account with appropriate permissions
"""

import os
import sys
import json
from typing import Dict, List, Optional
import stripe
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

# Configure Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

if not stripe.api_key:
    print("❌ Error: STRIPE_SECRET_KEY environment variable not set")
    print("Please set your Stripe secret key and run this script again.")
    sys.exit(1)

# Product configurations
PRODUCTS = {
    'pro': {
        'name': 'CapitolScope Pro',
        'description': 'Advanced congressional trading insights for serious investors',
        'features': [
            'Full historical trading data',
            'Weekly summaries',
            'Multiple buyer alerts',
            'High-value trade alerts',
            'Saved portfolios & watchlists',
            'Export to CSV'
        ],
        'pricing': {
            'month': 599,  # $5.99
            'year': 5999   # $59.99
        }
    },
    'premium': {
        'name': 'CapitolScope Premium',
        'description': 'Professional-grade tools for power users and analysts',
        'features': [
            'Everything in Pro',
            'TradingView-style charts',
            'Advanced portfolio analytics',
            'Sector/committee-based filters',
            'API access (rate-limited)',
            'Custom alert configurations'
        ],
        'pricing': {
            'month': 1499,  # $14.99
            'year': 14999   # $149.99
        }
    },
    'enterprise': {
        'name': 'CapitolScope Enterprise',
        'description': 'Complete solution for organizations and teams',
        'features': [
            'Everything in Premium',
            'Advanced analytics dashboard',
            'White-label dashboard options',
            'Priority support',
            'Increased API limits',
            'Team seats & admin panel'
        ],
        'pricing': {
            'month': 4999,  # $49.99
            'year': 49999   # $499.99
        }
    }
}

def create_product(product_key: str, product_config: Dict) -> Dict:
    """Create a Stripe product."""
    try:
        product = stripe.Product.create(
            name=product_config['name'],
            description=product_config['description'],
            metadata={
                'product_key': product_key,
                'features': json.dumps(product_config['features']),
                'created_by': 'capitolscope_setup_script'
            }
        )
        print(f"✅ Created product: {product.name} (ID: {product.id})")
        return product
    except stripe.error.StripeError as e:
        print(f"❌ Error creating product {product_key}: {e}")
        return None

def create_price(product_id: str, amount: int, interval: str, currency: str = 'usd') -> Optional[str]:
    """Create a Stripe price for a product."""
    try:
        price = stripe.Price.create(
            product=product_id,
            unit_amount=amount,
            currency=currency,
            recurring={'interval': interval},
            metadata={
                'interval': interval,
                'created_by': 'capitolscope_setup_script'
            }
        )
        print(f"✅ Created {interval} price: ${amount/100:.2f} (ID: {price.id})")
        return price.id
    except stripe.error.StripeError as e:
        print(f"❌ Error creating price for {interval}: {e}")
        return None

def setup_products():
    """Set up all products and pricing plans."""
    print("🚀 Setting up Stripe products for CapitolScope...")
    print("=" * 60)
    
    results = {}
    
    for product_key, product_config in PRODUCTS.items():
        print(f"\n📦 Creating {product_key.upper()} product...")
        
        # Create the product
        product = create_product(product_key, product_config)
        if not product:
            continue
            
        results[product_key] = {
            'product_id': product.id,
            'prices': {}
        }
        
        # Create monthly and yearly prices
        for interval, amount in product_config['pricing'].items():
            price_id = create_price(product.id, amount, interval)
            if price_id:
                results[product_key]['prices'][interval] = price_id
    
    return results

def generate_env_file(results: Dict):
    """Generate environment variables for the created products."""
    print("\n" + "=" * 60)
    print("📝 Environment Variables to add to your .env file:")
    print("=" * 60)
    
    env_vars = []
    
    for product_key, product_data in results.items():
        env_vars.append(f"STRIPE_PRODUCT_{product_key.upper()}_MONTHLY={product_data['product_id']}")
        env_vars.append(f"STRIPE_PRODUCT_{product_key.upper()}_YEARLY={product_data['product_id']}")
        
        # Add price IDs
        if 'month' in product_data['prices']:
            env_vars.append(f"STRIPE_PRICE_{product_key.upper()}_MONTHLY={product_data['prices']['month']}")
        if 'year' in product_data['prices']:
            env_vars.append(f"STRIPE_PRICE_{product_key.upper()}_YEARLY={product_data['prices']['year']}")
    
    for var in env_vars:
        print(var)
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"stripe_products_{timestamp}.env"
    
    with open(filename, 'w') as f:
        f.write("# Stripe Product IDs generated by setup script\n")
        f.write(f"# Generated on: {datetime.now().isoformat()}\n\n")
        for var in env_vars:
            f.write(f"{var}\n")
    
    print(f"\n💾 Product IDs saved to: {filename}")

def main():
    """Main execution function."""
    print("🎯 CapitolScope Stripe Products Setup")
    print("=" * 60)
    
    # Verify Stripe connection
    try:
        stripe.Account.retrieve()
        print("✅ Stripe connection successful")
    except stripe.error.AuthenticationError:
        print("❌ Invalid Stripe API key")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Stripe connection failed: {e}")
        sys.exit(1)
    
    # Set up products
    results = setup_products()
    
    if results:
        generate_env_file(results)
        print(f"\n🎉 Successfully created {len(results)} products!")
        print("\nNext steps:")
        print("1. Copy the environment variables above to your .env file")
        print("2. Update your frontend with the new product IDs")
        print("3. Test the integration with Stripe Checkout")
    else:
        print("\n❌ No products were created successfully")

if __name__ == "__main__":
    main()
