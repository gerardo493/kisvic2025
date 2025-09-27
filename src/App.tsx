import React, { useState } from 'react';
import Dashboard from './pages/Dashboard';
import StatsCardExample from './examples/StatsCardExample';
import './index.css';

function App() {
  const [showExample, setShowExample] = useState(false);

  return (
    <div className="App">
      <div className="fixed top-4 right-4 z-50">
        <button
          onClick={() => setShowExample(!showExample)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg shadow-lg transition-colors duration-200"
        >
          {showExample ? 'Ver Dashboard' : 'Ver Ejemplo StatsCard'}
        </button>
      </div>
      
      {showExample ? <StatsCardExample /> : <Dashboard />}
    </div>
  );
}

export default App;
