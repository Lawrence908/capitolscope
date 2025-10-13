# 🚨 Frontend Trade Alert System Implementation Plan

## 📋 **Project Overview**

**Goal:** Implement frontend UI components for the trade alert notification system, allowing users to create, manage, and monitor congressional trade alerts.

**Key Features:**
- Member-specific trade alerts (e.g., "Notify me when MTG trades")
- Amount-based alerts (e.g., "Notify me of all trades $1M+")
- Ticker-specific alerts (e.g., "Notify me when anyone trades TSLA")
- Alert management dashboard
- Notification preferences

---

## 🏗️ **Architecture Overview**

```
Frontend Components → API Endpoints → Alert Engine → Email Notifications
       ↓                   ↓              ↓              ↓
  Alert Dashboard → POST /alerts/member → TradeAlertRule → Email Delivery
  Manage Alerts   → GET /alerts/rules   → Alert Engine   → Notification Tracking
  Preferences     → PUT /alerts/rules   → Background Task → Delivery Status
```

---

## 📁 **Frontend Implementation Structure**

### **Phase 1: Core Components (2-3 days)**

#### **1.1 Alert Dashboard Page**
```typescript
// File: frontend/src/pages/alerts/AlertDashboard.tsx
```

**Purpose:** Main dashboard for viewing and managing all user alerts.

**Key Features:**
- Overview of active alerts
- Quick stats (total alerts, notifications sent today)
- Recent alert activity
- Quick action buttons

#### **1.2 Create Alert Modal**
```typescript
// File: frontend/src/components/alerts/CreateAlertModal.tsx
```

**Purpose:** Modal for creating new trade alerts with different types.

**Key Features:**
- Alert type selector (Member/Amount/Ticker)
- Dynamic form fields based on alert type
- Validation and error handling
- Preview of alert configuration

#### **1.3 Alert Management Table**
```typescript
// File: frontend/src/components/alerts/AlertTable.tsx
```

**Purpose:** Table component for listing and managing existing alerts.

**Key Features:**
- Sortable columns (name, type, created date, status)
- Filter by alert type and status
- Inline edit and delete actions
- Bulk operations

### **Phase 2: Alert Type Components (1-2 days)**

#### **2.1 Member Alert Creator**
```typescript
// File: frontend/src/components/alerts/MemberAlertForm.tsx
```

**Features:**
- Member search with autocomplete
- Member selection with photo and basic info
- Alert name and description fields
- Notification channel selection

#### **2.2 Amount Alert Creator**
```typescript
// File: frontend/src/components/alerts/AmountAlertForm.tsx
```

**Features:**
- Amount threshold input with validation
- Currency formatting
- Visual threshold indicators
- Examples of typical amounts

#### **2.3 Ticker Alert Creator**
```typescript
// File: frontend/src/components/alerts/TickerAlertForm.tsx
```

**Features:**
- Ticker symbol search with autocomplete
- Company name display
- Stock price and basic info
- Alert name auto-generation

### **Phase 3: Notification Management (1 day)**

#### **3.1 Notification Preferences**
```typescript
// File: frontend/src/components/alerts/NotificationPreferences.tsx
```

**Features:**
- Email notification toggle
- Frequency settings (immediate, daily digest)
- Email address verification
- Test notification button

#### **3.2 Alert History**
```typescript
// File: frontend/src/components/alerts/AlertHistory.tsx
```

**Features:**
- Timeline of triggered alerts
- Delivery status indicators
- Re-send functionality
- Filter by date range and status

---

## 🔧 **Detailed Component Implementation**

### **Step 1: Alert Dashboard Page**

```typescript
// frontend/src/pages/alerts/AlertDashboard.tsx

import React, { useState, useEffect } from 'react';
import { Card, Button, Stat, StatLabel, StatNumber, StatHelpText } from '@chakra-ui/react';
import { useToast } from '@chakra-ui/react';
import { AlertTable } from '@/components/alerts/AlertTable';
import { CreateAlertModal } from '@/components/alerts/CreateAlertModal';
import { NotificationPreferences } from '@/components/alerts/NotificationPreferences';
import { useAlerts } from '@/hooks/useAlerts';

export const AlertDashboard: React.FC = () => {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedTab, setSelectedTab] = useState('alerts');
  const { alerts, stats, loading, error, refetch } = useAlerts();
  const toast = useToast();

  const handleCreateAlert = async (alertData: any) => {
    try {
      await createAlert(alertData);
      toast({
        title: 'Alert created successfully',
        status: 'success',
        duration: 3000,
      });
      setIsCreateModalOpen(false);
      refetch();
    } catch (error) {
      toast({
        title: 'Failed to create alert',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Trade Alerts</h1>
            <p className="text-gray-600 mt-2">
              Get notified when congress members make trades matching your criteria
            </p>
          </div>
          <Button
            colorScheme="blue"
            size="lg"
            onClick={() => setIsCreateModalOpen(true)}
          >
            Create Alert
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card p={6}>
            <Stat>
              <StatLabel>Active Alerts</StatLabel>
              <StatNumber>{stats?.activeAlerts || 0}</StatNumber>
              <StatHelpText>Currently monitoring</StatHelpText>
            </Stat>
          </Card>
          <Card p={6}>
            <Stat>
              <StatLabel>Notifications Today</StatLabel>
              <StatNumber>{stats?.notificationsToday || 0}</StatNumber>
              <StatHelpText>Alerts triggered</StatHelpText>
            </Stat>
          </Card>
          <Card p={6}>
            <Stat>
              <StatLabel>Total Triggered</StatLabel>
              <StatNumber>{stats?.totalTriggered || 0}</StatNumber>
              <StatHelpText>All time</StatHelpText>
            </Stat>
          </Card>
          <Card p={6}>
            <Stat>
              <StatLabel>Delivery Rate</StatLabel>
              <StatNumber>{stats?.deliveryRate || 0}%</StatNumber>
              <StatHelpText>Email success rate</StatHelpText>
            </Stat>
          </Card>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {['alerts', 'history', 'preferences'].map((tab) => (
              <button
                key={tab}
                onClick={() => setSelectedTab(tab)}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  selectedTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-lg shadow">
          {selectedTab === 'alerts' && (
            <AlertTable 
              alerts={alerts} 
              loading={loading} 
              onRefetch={refetch}
            />
          )}
          {selectedTab === 'history' && (
            <AlertHistory />
          )}
          {selectedTab === 'preferences' && (
            <NotificationPreferences />
          )}
        </div>

        {/* Create Alert Modal */}
        <CreateAlertModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onSubmit={handleCreateAlert}
        />
      </div>
    </div>
  );
};
```

### **Step 2: Create Alert Modal**

```typescript
// frontend/src/components/alerts/CreateAlertModal.tsx

import React, { useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  VStack,
  HStack,
  Text,
  Icon,
  useToast,
} from '@chakra-ui/react';
import { MemberAlertForm } from './MemberAlertForm';
import { AmountAlertForm } from './AmountAlertForm';
import { TickerAlertForm } from './TickerAlertForm';

interface CreateAlertModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (alertData: any) => Promise<void>;
}

export const CreateAlertModal: React.FC<CreateAlertModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [selectedType, setSelectedType] = useState<string>('');
  const [formData, setFormData] = useState<any>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const alertTypes = [
    {
      id: 'member_trades',
      name: 'Member Trades',
      description: 'Get notified when a specific congress member makes trades',
      icon: '👤',
      example: 'MTG, Nancy Pelosi, etc.',
    },
    {
      id: 'amount_threshold',
      name: 'Large Trades',
      description: 'Get notified when any member makes trades above a certain amount',
      icon: '💰',
      example: '$1M+, $500K+, etc.',
    },
    {
      id: 'ticker_trades',
      name: 'Stock Alerts',
      description: 'Get notified when any member trades a specific stock',
      icon: '📈',
      example: 'TSLA, AAPL, NVDA, etc.',
    },
  ];

  const handleSubmit = async () => {
    if (!selectedType || !formData) return;

    setIsSubmitting(true);
    try {
      await onSubmit({
        alert_type: selectedType,
        ...formData,
      });
      // Reset form
      setSelectedType('');
      setFormData({});
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderForm = () => {
    switch (selectedType) {
      case 'member_trades':
        return <MemberAlertForm onDataChange={setFormData} />;
      case 'amount_threshold':
        return <AmountAlertForm onDataChange={setFormData} />;
      case 'ticker_trades':
        return <TickerAlertForm onDataChange={setFormData} />;
      default:
        return null;
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Create New Trade Alert</ModalHeader>
        <ModalBody>
          {!selectedType ? (
            <VStack spacing={4}>
              <Text fontSize="md" color="gray.600" textAlign="center">
                Choose the type of trade alert you want to create
              </Text>
              
              {alertTypes.map((type) => (
                <Button
                  key={type.id}
                  variant="outline"
                  size="lg"
                  height="auto"
                  p={6}
                  w="full"
                  onClick={() => setSelectedType(type.id)}
                  _hover={{ bg: 'blue.50', borderColor: 'blue.300' }}
                >
                  <VStack spacing={2} align="start" w="full">
                    <HStack>
                      <Text fontSize="2xl">{type.icon}</Text>
                      <Text fontWeight="bold" fontSize="lg">
                        {type.name}
                      </Text>
                    </HStack>
                    <Text fontSize="sm" color="gray.600" textAlign="left">
                      {type.description}
                    </Text>
                    <Text fontSize="xs" color="blue.500" fontWeight="medium">
                      Example: {type.example}
                    </Text>
                  </VStack>
                </Button>
              ))}
            </VStack>
          ) : (
            <VStack spacing={6}>
              <HStack>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedType('')}
                >
                  ← Back
                </Button>
                <Text fontWeight="bold">
                  {alertTypes.find(t => t.id === selectedType)?.name}
                </Text>
              </HStack>
              
              {renderForm()}
            </VStack>
          )}
        </ModalBody>
        
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Cancel
          </Button>
          {selectedType && (
            <Button
              colorScheme="blue"
              onClick={handleSubmit}
              isLoading={isSubmitting}
              isDisabled={!formData || Object.keys(formData).length === 0}
            >
              Create Alert
            </Button>
          )}
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
```

### **Step 3: API Integration Hook**

```typescript
// frontend/src/hooks/useAlerts.ts

import { useState, useEffect } from 'react';
import { useToast } from '@chakra-ui/react';
import { apiClient } from '@/lib/api';

export interface TradeAlert {
  id: string;
  name: string;
  alert_type: 'member_trades' | 'amount_threshold' | 'ticker_trades';
  target_id?: number;
  target_symbol?: string;
  target_name?: string;
  threshold_value?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AlertStats {
  activeAlerts: number;
  notificationsToday: number;
  totalTriggered: number;
  deliveryRate: number;
}

export const useAlerts = () => {
  const [alerts, setAlerts] = useState<TradeAlert[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/notifications/alerts/rules');
      setAlerts(response.data.data.items);
      setError(null);
    } catch (err) {
      setError(err.message);
      toast({
        title: 'Failed to load alerts',
        description: err.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      // Mock stats for now - implement when analytics endpoint is ready
      setStats({
        activeAlerts: alerts.filter(a => a.is_active).length,
        notificationsToday: 0,
        totalTriggered: 0,
        deliveryRate: 95,
      });
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const createAlert = async (alertData: any) => {
    const endpoint = {
      member_trades: `/notifications/alerts/member/${alertData.target_id}`,
      amount_threshold: '/notifications/alerts/amount',
      ticker_trades: `/notifications/alerts/ticker/${alertData.target_symbol}`,
    }[alertData.alert_type];

    const response = await apiClient.post(endpoint, alertData);
    return response.data;
  };

  const updateAlert = async (alertId: string, updates: Partial<TradeAlert>) => {
    const response = await apiClient.put(`/notifications/alerts/rules/${alertId}`, updates);
    return response.data;
  };

  const deleteAlert = async (alertId: string) => {
    const response = await apiClient.delete(`/notifications/alerts/rules/${alertId}`);
    return response.data;
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  useEffect(() => {
    if (alerts.length > 0) {
      fetchStats();
    }
  }, [alerts]);

  return {
    alerts,
    stats,
    loading,
    error,
    refetch: fetchAlerts,
    createAlert,
    updateAlert,
    deleteAlert,
  };
};
```

---

## 🎯 **Quick Start Implementation Guide**

### **Day 1: Setup & Dashboard**
1. Create alert dashboard page structure
2. Implement basic alert table component
3. Add create alert button and modal shell

### **Day 2: Alert Creation**
1. Implement create alert modal with type selection
2. Build member alert form with member search
3. Add form validation and error handling

### **Day 3: Complete Alert Types**
1. Build amount threshold alert form
2. Build ticker alert form with stock search
3. Integrate all forms with API endpoints

### **Day 4: Management Features**
1. Add edit/delete functionality to alert table
2. Implement alert history timeline
3. Add notification preferences panel

### **Day 5: Polish & Testing**
1. Add loading states and error handling
2. Implement responsive design
3. Add confirmation dialogs and toast notifications
4. Test all user flows

---

## 📊 **Testing Strategy**

### **Unit Tests**
- Alert form validation
- API hook functions
- Component rendering

### **Integration Tests**
- Complete alert creation flow
- Alert management operations
- API integration

### **E2E Tests**
- User creates MTG alert
- User manages existing alerts
- User receives notifications

---

## 🚀 **Deployment Checklist**

### **Environment Variables**
```bash
NEXT_PUBLIC_API_URL=https://api.capitolscope.chrislawrence.ca
NEXT_PUBLIC_FEATURE_ALERTS=true
```

### **Feature Flags**
```typescript
export const FEATURES = {
  TRADE_ALERTS: process.env.NEXT_PUBLIC_FEATURE_ALERTS === 'true',
  ALERT_HISTORY: true,
  BULK_OPERATIONS: false, // Coming soon
};
```

This implementation provides a complete, user-friendly interface for Kyle to set up his MTG alerts and for other users to create their own custom trade notifications! 🎯



