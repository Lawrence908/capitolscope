import React from 'react';
import { useParams } from 'react-router-dom';
import { PageHeader } from '../../components/ui';

// Placeholder: the public trade permalink page (/t/:tradeId) is built out
// in the Bulletin redesign.
const TradePage: React.FC = () => {
  const { tradeId } = useParams();
  return <PageHeader title="Trade" subtitle={`Trade ${tradeId ?? ''}`} />;
};

export default TradePage;
