import { useState, useEffect } from "react";
import { Bell, Plus, Trash2 } from "lucide-react";

interface AlertData {
  id: string;
  symbol: string | null;
  alert_type: string;
  threshold: number | null;
  name: string;
  enabled: boolean;
  is_triggered: boolean;
  triggered_at: string | null;
  created_at: string;
}

export default function AlertsManager() {
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [loading, setLoading] = useState(true);
  const [newSymbol, setNewSymbol] = useState("");
  const [newThreshold, setNewThreshold] = useState("");
  const [newType, setNewType] = useState("PRICE_ABOVE");

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const token = localStorage.getItem("token") || "";
      const res = await fetch(`${apiUrl}/api/v1/alerts`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAlerts(data.alerts || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const createAlert = async () => {
    if (!newSymbol || !newThreshold) return;
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const token = localStorage.getItem("token") || "";
      const payload = {
        symbol: newSymbol.toUpperCase(),
        alert_type: newType,
        threshold: parseFloat(newThreshold),
        name: `${newSymbol.toUpperCase()} ${newType.replace("_", " ")} ${newThreshold}`,
        enabled: true
      };
      
      const res = await fetch(`${apiUrl}/api/v1/alerts`, {
        method: "POST",
        headers: { 
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        setAlerts([...alerts, data]);
        setNewSymbol("");
        setNewThreshold("");
      } else {
        const err = await res.json();
        alert(`Failed to create alert: ${err.detail}`);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const deleteAlert = async (id: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const token = localStorage.getItem("token") || "";
      const res = await fetch(`${apiUrl}/api/v1/alerts/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        setAlerts(alerts.filter(a => a.id !== id));
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="flex h-full flex-col bg-[var(--nq-bg-surface)] p-4 overflow-y-auto custom-scrollbar">
      <h2 className="text-sm font-bold text-[var(--nq-text-primary)] mb-4 flex items-center gap-2">
        <Bell className="w-4 h-4 text-[var(--nq-accent-cyan)]" /> AI Price Alerts
      </h2>
      
      {/* Create Alert Form */}
      <div className="mb-6 rounded-lg border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-3 shadow-inner">
        <h3 className="text-xs font-semibold text-[var(--nq-text-secondary)] mb-3">Create New Alert</h3>
        <div className="flex flex-col gap-2">
          <div className="flex flex-col md:flex-row gap-2">
            <input 
              type="text" 
              placeholder="Symbol (e.g. AAPL)" 
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              className="flex-1 rounded border border-[var(--nq-border)] bg-[rgba(0,0,0,0.2)] px-2 py-1.5 min-h-[44px] md:min-h-0 text-xs text-[var(--nq-text-primary)] focus:border-[var(--nq-accent-cyan)] outline-none transition-colors"
            />
            <select 
              value={newType}
              onChange={(e) => setNewType(e.target.value)}
              className="rounded border border-[var(--nq-border)] bg-[rgba(0,0,0,0.2)] px-2 py-1.5 min-h-[44px] md:min-h-0 text-xs text-[var(--nq-text-primary)] focus:border-[var(--nq-accent-cyan)] outline-none transition-colors"
            >
              <option value="PRICE_ABOVE">Price Above</option>
              <option value="PRICE_BELOW">Price Below</option>
            </select>
          </div>
          <div className="flex flex-col md:flex-row gap-2">
            <input 
              type="number" 
              placeholder="Threshold (e.g. 150)" 
              value={newThreshold}
              onChange={(e) => setNewThreshold(e.target.value)}
              className="flex-1 rounded border border-[var(--nq-border)] bg-[rgba(0,0,0,0.2)] px-2 py-1.5 min-h-[44px] md:min-h-0 text-xs text-[var(--nq-text-primary)] focus:border-[var(--nq-accent-cyan)] outline-none transition-colors"
            />
            <button 
              onClick={createAlert}
              disabled={!newSymbol || !newThreshold}
              className="flex items-center justify-center gap-1 rounded bg-[var(--nq-accent-cyan)] px-3 py-1.5 min-h-[44px] md:min-h-0 text-xs font-bold text-black hover:bg-[#00e6ff] transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_10px_rgba(0,212,245,0.3)]"
            >
              <Plus className="w-3 h-3" /> Add
            </button>
          </div>
        </div>
      </div>
      
      {/* Alert List */}
      <h3 className="text-xs font-semibold text-[var(--nq-text-secondary)] mb-3">Active Alerts</h3>
      {loading ? (
        <div className="text-xs text-[var(--nq-text-muted)] animate-pulse">Loading alerts...</div>
      ) : alerts.length === 0 ? (
        <div className="text-xs text-[var(--nq-text-muted)] p-4 text-center border border-dashed border-[var(--nq-border)] rounded bg-[rgba(255,255,255,0.01)]">
          No active alerts. Add one above.
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {alerts.map((alert) => (
            <div key={alert.id} className={`flex items-center justify-between p-2.5 rounded border ${alert.is_triggered ? 'border-[var(--accent-green)] bg-[rgba(0,230,118,0.08)] shadow-[0_0_10px_rgba(0,230,118,0.1)]' : 'border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] hover:border-[rgba(255,255,255,0.15)]'} transition-colors group`}>
              <div className="flex flex-col">
                <span className="text-xs font-bold font-mono text-[var(--nq-text-primary)] flex items-center gap-2">
                  {alert.symbol} 
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-sans font-semibold ${alert.alert_type === 'PRICE_ABOVE' ? 'bg-[rgba(0,230,118,0.15)] text-[var(--accent-green)]' : 'bg-[rgba(255,59,92,0.15)] text-[var(--accent-red)]'}`}>
                    {alert.alert_type === 'PRICE_ABOVE' ? '↑' : '↓'} {alert.threshold}
                  </span>
                </span>
                {alert.is_triggered ? (
                  <span className="text-[9px] text-[var(--accent-green)] font-semibold mt-1">Triggered at {new Date(alert.triggered_at!).toLocaleString()}</span>
                ) : (
                  <span className="text-[9px] text-[var(--nq-text-muted)] mt-1 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--nq-accent-cyan)] animate-pulse" /> Active monitoring
                  </span>
                )}
              </div>
              <button onClick={() => deleteAlert(alert.id)} className="p-1.5 rounded text-[var(--nq-text-secondary)] hover:bg-[rgba(255,59,92,0.15)] hover:text-[#FF3B5C] transition-colors opacity-50 group-hover:opacity-100">
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
