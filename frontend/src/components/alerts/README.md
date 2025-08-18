# Trade Alerts Frontend Implementation

This directory contains the frontend implementation of the trade alert notification system for CapitolScope.

## 🏗️ Architecture

The trade alerts system consists of several interconnected components:

### Core Components

1. **AlertDashboard** (`/pages/alerts/AlertDashboard.tsx`)
   - Main dashboard page accessible at `/alerts`
   - Displays statistics, alert management table, and navigation tabs
   - Integrates all other alert components

2. **CreateAlertModal** (`CreateAlertModal.tsx`)
   - Modal for creating new trade alerts
   - Provides three alert types: Member Trades, Amount Threshold, Stock Alerts
   - Dynamic form rendering based on selected alert type

3. **Alert Forms**
   - **MemberAlertForm**: Create alerts for specific congress members
   - **AmountAlertForm**: Create alerts for trades above certain amounts
   - **TickerAlertForm**: Create alerts for specific stock symbols

4. **AlertTable** (`AlertTable.tsx`)
   - Table for managing existing alerts
   - Sortable columns, filtering, and inline actions
   - Toggle active/inactive status, delete alerts

5. **Management Components**
   - **NotificationPreferences**: Configure email settings and delivery preferences
   - **AlertHistory**: View notification delivery history and status

## 🔧 API Integration

The system uses a custom hook (`/hooks/useAlerts.ts`) that provides:

- `alerts`: Array of user's trade alerts
- `stats`: Dashboard statistics
- `loading`: Loading state
- `createAlert()`: Create new alerts
- `updateAlert()`: Modify existing alerts
- `deleteAlert()`: Remove alerts
- `toggleAlert()`: Enable/disable alerts

## 🛠️ Technologies Used

- **React 18** with TypeScript
- **React Router** for navigation
- **TailwindCSS** for styling
- **Heroicons** for icons
- **Axios** for API calls

## 📱 Features

### Alert Types
1. **Member Trades**: Get notified when specific congress members trade
2. **Amount Threshold**: Get notified for trades above a certain value
3. **Stock Alerts**: Get notified when any member trades specific stocks

### Dashboard Features
- Real-time statistics display
- Alert management table with sorting and filtering
- Notification preferences configuration
- Alert history and delivery tracking

### User Experience
- Responsive design for mobile and desktop
- Intuitive alert creation flow
- Real-time status updates
- Error handling and loading states

## 🚀 Getting Started

The alerts system is fully integrated into the main application. Users can access it via:

1. Navigation menu: "Trade Alerts" 
2. Direct URL: `/alerts`
3. Must be logged in (protected route)

## 🔮 Future Enhancements

- Push notifications for mobile
- Slack/Discord integration
- Advanced filtering options
- Bulk alert operations
- Alert templates
- Performance analytics
