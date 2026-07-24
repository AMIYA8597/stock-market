import React, { useState, useEffect } from 'react';
import api from './api';
import { io } from 'socket.io-client';
import Chart from './components/Chart';
import './styles.css';

function App() {
  const [ticker, setTicker] = useState('NIFTY');
  const [priceData, setPriceData] = useState([]);
  const [indicators, setIndicators] = useState([]);
  const [signal, setSignal] = useState(null);
  const [socket, setSocket] = useState(null);

  // Fetch historical OHLC + indicators on ticker change
  useEffect(() => {
    const fetchData = async () => {
      try {
        const histRes = await axios.get(`/historical/${ticker}`, { params: { days: 30 } });
        const candles = histRes.data.map(d => ({
          time: Math.floor(new Date(d.time).getTime() / 1000), // seconds epoch for chart lib
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close
        }));
        setPriceData(candles);
        const indRes = await axios.get(`/indicators/${ticker}`, { params: { days: 30 } });
        setIndicators(indRes.data);
        const sigRes = await axios.get(`/signal/${ticker}`, { params: { days: 30 } });
        setSignal(sigRes.data.signal);
      } catch (err) {
        console.error('Error loading data', err);
      }
    };
    fetchData();
  }, [ticker]);

  // Setup WebSocket for live price updates
  useEffect(() => {
    const s = io('http://localhost:5000', { path: '/socket.io' });
    s.on('connect', () => console.log('Socket connected'));
    s.on('price_update', data => {
      const point = {
        time: Math.floor(new Date(data.time).getTime() / 1000),
        open: data.open,
        high: data.high,
        low: data.low,
        close: data.close
      };
      setPriceData(prev => [...prev.slice(-29), point]); // keep last 30 points
    });
    setSocket(s);
    return () => {
      s.disconnect();
    };
  }, []);

  const handleTickerChange = e => setTicker(e.target.value.toUpperCase());

  return (
    <div className="app-container">
      <header className="header">
        <h1>AI‑Driven Stock Trading Dashboard</h1>
        <div className="ticker-select">
          <label htmlFor="ticker">Ticker:&nbsp;</label>
          <input id="ticker" value={ticker} onChange={handleTickerChange} />
        </div>
        {signal && (
          <div className={`signal-box ${signal.toLowerCase()}`}>Signal: {signal}</div>
        )}
      </header>
      <main className="main">
        <Chart candles={priceData} indicators={indicators} />
      </main>
      <footer className="footer">© 2026 Stock‑AI</footer>
    </div>
  );
}

export default App;
