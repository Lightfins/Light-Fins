import React, { useState } from 'react';
import MainLayout from './components/Layout/MainLayout';
import ProductSelection from './components/ProductSelection/ProductSelection';
import WizardContainer from './components/Wizard/WizardContainer';
import './App.css';
import './components/Wizard/Wizard.css';

function App() {
  const [view, setView] = useState('selection'); // 'selection' | 'chat'
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [showQR, setShowQR] = useState(false);
  const shareUrl = window.location.href;

  const handleSelectPlan = (plan: any) => {
    setSelectedPlan(plan);
    setView('chat');
  };

  return (
    <MainLayout>
      {/* Share Button - Always visible in chat */}
      {view === 'chat' && (
        <button
          onClick={() => setShowQR(!showQR)}
          className="share-btn"
          style={{
            position: 'fixed',
            top: '20px',
            right: '20px',
            background: 'var(--wc-accent, #E8AF30)',
            color: 'white',
            border: 'none',
            borderRadius: '50%',
            width: '50px',
            height: '50px',
            fontSize: '24px',
            cursor: 'pointer',
            boxShadow: 'var(--shadow)',
            zIndex: 1000
          }}
          title="Share App"
        >
          📱
        </button>
      )}

      {view === 'selection' && (
        <ProductSelection onSelectPlan={handleSelectPlan} />
      )}

      {view === 'chat' && (
        <WizardContainer />
      )}
    </MainLayout>
  );
}

export default App;
