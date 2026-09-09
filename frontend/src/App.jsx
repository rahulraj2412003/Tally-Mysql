import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  BookOpen,
  Check,
  CircleAlert,
  Database,
  FileText,
  Layers3,
  LoaderCircle,
  RefreshCw,
  Server,
  ShieldCheck,
  Sparkles,
  Table2,
  X,
} from "lucide-react";
import {
  apiRequest,
  getLedgerDetails,
  getLedgers,
  getSyncHistory,
  getVoucherEntries,
  getVouchers,
} from "./api";
import "./App.css";

const formatDate = (value) => {
  if (!value) return "No sync recorded";
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(
    new Date(value),
  );
};

const formatDateTime = (value) => {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
};

const today = new Date().toISOString().slice(0, 10);

function App() {
  const [ledgers, setLedgers] = useState([]);
  const [vouchers, setVouchers] = useState([]);
  const [entries, setEntries] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState("");
  const [notice, setNotice] = useState(null);
  const [confirmFullSync, setConfirmFullSync] = useState(false);
  const [fromDate, setFromDate] = useState("2026-04-01");
  const [toDate, setToDate] = useState(today);
  const [voucherTypeFilter, setVoucherTypeFilter] = useState("");
  const [voucherFromDate, setVoucherFromDate] = useState("");
  const [voucherToDate, setVoucherToDate] = useState("");
  const [selectedLedgerId, setSelectedLedgerId] = useState(null);
  const [ledgerDetails, setLedgerDetails] = useState(null);
  const [ledgerDetailsLoading, setLedgerDetailsLoading] = useState(false);
  const [ledgerDetailsError, setLedgerDetailsError] = useState("");
  const dialogRef = useRef(null);

  const loadDashboard = async () => {
    const [ledgerData, voucherData, entryData, historyData] = await Promise.all(
      [getLedgers(), getVouchers(), getVoucherEntries(), getSyncHistory()],
    );
    setLedgers(ledgerData);
    setVouchers(voucherData);
    setEntries(entryData);
    setHistory(historyData);
  };

  const openLedgerDetails = async (ledgerId) => {
    setSelectedLedgerId(ledgerId);
    setLedgerDetails(null);
    setLedgerDetailsError("");
    setLedgerDetailsLoading(true);
    try {
      const response = await getLedgerDetails(ledgerId);
      setLedgerDetails(response.data);
    } catch (error) {
      setLedgerDetailsError(error.message);
    } finally {
      setLedgerDetailsLoading(false);
    }
  };

  const closeLedgerDetails = () => {
    setSelectedLedgerId(null);
    setLedgerDetails(null);
    setLedgerDetailsError("");
  };

  useEffect(() => {
    loadDashboard()
      .catch((error) => setNotice({ type: "error", text: error.message }))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (confirmFullSync) dialogRef.current?.showModal();
    else if (dialogRef.current?.open) dialogRef.current.close();
  }, [confirmFullSync]);

  const lastSync = useMemo(() => {
    const completed = history.find(
      (item) => item.status === "SUCCESS" && item.completed_at,
    );
    return completed?.completed_at;
  }, [history]);

  const voucherTypes = useMemo(
    () =>
      [
        ...new Set(
          vouchers.map((voucher) => voucher.voucher_type).filter(Boolean),
        ),
      ].sort(),
    [vouchers],
  );

  const filteredVouchers = useMemo(() => {
    return vouchers.filter((voucher) => {
      const matchesType =
        !voucherTypeFilter || voucher.voucher_type === voucherTypeFilter;
      const matchesFromDate =
        !voucherFromDate || voucher.voucher_date >= voucherFromDate;
      const matchesToDate =
        !voucherToDate || voucher.voucher_date <= voucherToDate;
      return matchesType && matchesFromDate && matchesToDate;
    });
  }, [vouchers, voucherTypeFilter, voucherFromDate, voucherToDate]);

  const clearVoucherFilters = () => {
    setVoucherTypeFilter("");
    setVoucherFromDate("");
    setVoucherToDate("");
  };

  const runAction = async (action, path, options = {}) => {
    setBusyAction(action);
    setNotice(null);
    try {
      const result = await apiRequest(path, { method: "POST", ...options });
      setNotice({
        type: "success",
        text: `${result.message} ${result.summary.inserted} inserted, ${result.summary.updated} updated.`,
      });
      await loadDashboard();
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusyAction("");
    }
  };

  const testConnection = async (name, path) => {
    setBusyAction(name);
    setNotice(null);
    try {
      const result = await apiRequest(path, { method: "POST" });
      setNotice({ type: "success", text: result.message });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusyAction("");
    }
  };

  const actionDisabled = Boolean(busyAction) || loading;

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">
            <Layers3 size={21} />
          </div>
          <div>
            <p className="eyebrow">Operations console</p>
            <h1>
              Tally <span>→</span> MySQL
            </h1>
          </div>
        </div>
        <div className="system-status">
          <span className="status-dot" /> System ready{" "}
          <span className="status-divider" /> FastAPI connected
        </div>
      </header>

      <section className="intro-row">
        <div>
          <p className="eyebrow accent-text">Integration dashboard</p>
          <h2>Keep the books moving.</h2>
          <p className="intro-copy">
            Monitor connections, synchronize source data, and review the latest
            records from one quiet workspace.
          </p>
        </div>
        <div className="last-run">
          <span>LAST SUCCESSFUL SYNC</span>
          <strong>{loading ? "Loading…" : formatDateTime(lastSync)}</strong>
        </div>
      </section>

      {notice && (
        <div className={`notice ${notice.type}`}>
          <span>
            {notice.type === "success" ? (
              <Check size={17} />
            ) : (
              <CircleAlert size={17} />
            )}
          </span>
          {notice.text}
          <button
            className="icon-button"
            onClick={() => setNotice(null)}
            aria-label="Dismiss message"
          >
            <X size={16} />
          </button>
        </div>
      )}

      <section className="connection-grid">
        <ConnectionCard
          icon={<Server />}
          title="TallyPrime"
          subtitle="Source system"
          onTest={() => testConnection("tally", "/api/tally/test")}
          loading={busyAction === "tally"}
          disabled={actionDisabled}
        />
        <ConnectionCard
          icon={<Database />}
          title="MySQL"
          subtitle="Destination database"
          onTest={() => testConnection("mysql", "/api/mysql/test")}
          loading={busyAction === "mysql"}
          disabled={actionDisabled}
        />
      </section>

      <section className="metric-grid">
        <MetricCard
          icon={<BookOpen />}
          label="Total ledgers"
          value={loading ? "—" : ledgers.length}
          tone="teal"
        />
        <MetricCard
          icon={<FileText />}
          label="Total vouchers"
          value={loading ? "—" : vouchers.length}
          tone="gold"
        />
        <MetricCard
          icon={<Table2 />}
          label="Voucher entries"
          value={loading ? "—" : entries.length}
          tone="coral"
        />
        <MetricCard
          icon={<Activity />}
          label="Last sync"
          value={loading ? "—" : formatDate(lastSync)}
          tone="ink"
        />
      </section>

      <section className="work-grid">
        <div className="panel sync-panel">
          <PanelHeading
            icon={<RefreshCw />}
            title="Synchronization"
            subtitle="Run data flows in the correct order."
          />
          <div className="sync-actions">
            <ActionButton
              icon={<BookOpen size={17} />}
              label="Sync ledgers"
              onClick={() => runAction("ledgers", "/api/sync/ledgers")}
              disabled={actionDisabled}
              loading={busyAction === "ledgers"}
            />
            <ActionButton
              primary
              icon={<Sparkles size={17} />}
              label="Full sync"
              onClick={() => setConfirmFullSync(true)}
              disabled={actionDisabled}
              loading={busyAction === "full"}
            />
            <ActionButton
              icon={<ArrowDownToLine size={17} />}
              label="Incremental sync"
              onClick={() => runAction("incremental", "/api/sync/incremental")}
              disabled={actionDisabled}
              loading={busyAction === "incremental"}
            />
          </div>
          <p className="muted-note">
            <ShieldCheck size={15} /> Date-window based with idempotent upserts.
          </p>
        </div>

        <div className="panel voucher-panel">
          <PanelHeading
            icon={<FileText />}
            title="Voucher sync"
            subtitle="Choose a date window from TallyPrime."
          />
          <div className="date-fields">
            <label>
              From date
              <input
                type="date"
                value={fromDate}
                onChange={(event) => setFromDate(event.target.value)}
              />
            </label>
            <label>
              To date
              <input
                type="date"
                value={toDate}
                onChange={(event) => setToDate(event.target.value)}
              />
            </label>
          </div>
          <ActionButton
            primary
            icon={<RefreshCw size={17} />}
            label="Sync vouchers"
            onClick={() =>
              runAction("vouchers", "/api/sync/vouchers", {
                body: JSON.stringify({ from_date: fromDate, to_date: toDate }),
                headers: { "Content-Type": "application/json" },
              })
            }
            disabled={actionDisabled || !fromDate || !toDate}
            loading={busyAction === "vouchers"}
          />
        </div>
      </section>

      <section className="result-strip panel">
        <div className="result-label">
          <span className="result-icon">
            <Activity size={18} />
          </span>
          <div>
            <strong>Latest sync result</strong>
            <span>Activity from the most recent operation</span>
          </div>
        </div>
        <div className="result-stat">
          <span>Extracted</span>
          <strong>{history[0]?.extracted ?? "—"}</strong>
        </div>
        <div className="result-stat">
          <span>Inserted</span>
          <strong className="positive">{history[0]?.inserted ?? "—"}</strong>
        </div>
        <div className="result-stat">
          <span>Updated</span>
          <strong>{history[0]?.updated ?? "—"}</strong>
        </div>
        <div className="result-stat">
          <span>Failed</span>
          <strong className={history[0]?.failed ? "negative" : ""}>
            {history[0]?.failed ?? "—"}
          </strong>
        </div>
      </section>

      <section className="content-grid">
        <DataPanel
          title="Sync history"
          subtitle="Recent synchronization activity"
          icon={<Activity />}
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Records</th>
                  <th>Completed</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <LoadingRows columns={4} />
                ) : (
                  history.slice(0, 6).map((item) => (
                    <tr key={item.id}>
                      <td className="strong-cell">{item.sync_type}</td>
                      <td>
                        <span
                          className={`status-pill ${item.status.toLowerCase()}`}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td>{item.extracted ?? 0} extracted</td>
                      <td>
                        {formatDateTime(item.completed_at || item.started_at)}
                      </td>
                    </tr>
                  ))
                )}
                {!loading && !history.length && (
                  <EmptyRow
                    columns={4}
                    text="No synchronization history yet."
                  />
                )}
              </tbody>
            </table>
          </div>
        </DataPanel>
        <DataPanel
          title="Ledgers"
          subtitle={`${ledgers.length} records in MySQL`}
          icon={<BookOpen />}
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Parent</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <LoadingRows columns={3} />
                ) : (
                  ledgers.map((ledger) => (
                    <tr key={ledger.id}>
                      <td className="strong-cell">
                        <button
                          className="ledger-link"
                          type="button"
                          onClick={() => openLedgerDetails(ledger.id)}
                        >
                          {ledger.name}
                        </button>
                      </td>
                      <td>{ledger.parent || "—"}</td>
                      <td>{formatDate(ledger.updated_at)}</td>
                    </tr>
                  ))
                )}
                {!loading && !ledgers.length && (
                  <EmptyRow columns={3} text="No ledgers synchronized yet." />
                )}
              </tbody>
            </table>
          </div>
        </DataPanel>
      </section>

      {selectedLedgerId !== null && (
        <LedgerDetailsPanel
          details={ledgerDetails}
          error={ledgerDetailsError}
          loading={ledgerDetailsLoading}
          onClose={closeLedgerDetails}
          onRetry={() => openLedgerDetails(selectedLedgerId)}
        />
      )}

      <DataPanel
        title="Vouchers"
        subtitle={`${filteredVouchers.length} of ${vouchers.length} records in MySQL`}
        icon={<FileText />}
      >
        <div className="voucher-filters" aria-label="Filter vouchers">
          <label>
            Voucher type
            <select
              value={voucherTypeFilter}
              onChange={(event) => setVoucherTypeFilter(event.target.value)}
            >
              <option value="">All types</option>
              {voucherTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label>
            From date
            <input
              type="date"
              value={voucherFromDate}
              onChange={(event) => setVoucherFromDate(event.target.value)}
            />
          </label>
          <label>
            To date
            <input
              type="date"
              value={voucherToDate}
              onChange={(event) => setVoucherToDate(event.target.value)}
            />
          </label>
          <button
            className="secondary-button clear-filter-button"
            type="button"
            onClick={clearVoucherFilters}
            disabled={!voucherTypeFilter && !voucherFromDate && !voucherToDate}
          >
            Clear filters
          </button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Number</th>
                <th>Narration</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <LoadingRows columns={5} />
              ) : (
                filteredVouchers.slice(0, 8).map((voucher) => (
                  <tr key={voucher.id}>
                    <td className="strong-cell">
                      {formatDate(voucher.voucher_date)}
                    </td>
                    <td>{voucher.voucher_type || "—"}</td>
                    <td>{voucher.voucher_number || "—"}</td>
                    <td className="truncate">{voucher.narration || "—"}</td>
                    <td>{formatDate(voucher.updated_at)}</td>
                  </tr>
                ))
              )}
              {!loading && !vouchers.length && (
                <EmptyRow columns={5} text="No vouchers synchronized yet." />
              )}
              {!loading && vouchers.length > 0 && !filteredVouchers.length && (
                <EmptyRow
                  columns={5}
                  text="No vouchers match the selected filters."
                />
              )}
            </tbody>
          </table>
        </div>
      </DataPanel>

      <dialog ref={dialogRef} onClose={() => setConfirmFullSync(false)}>
        <div className="dialog-icon">
          <CircleAlert size={21} />
        </div>
        <h3>Run a full synchronization?</h3>
        <p>
          This will reread ledgers and the full voucher date window. Existing
          records will be updated rather than duplicated.
        </p>
        <div className="dialog-actions">
          <button
            className="secondary-button"
            onClick={() => setConfirmFullSync(false)}
          >
            Cancel
          </button>
          <button
            className="primary-button"
            onClick={() => {
              setConfirmFullSync(false);
              runAction("full", "/api/sync/full");
            }}
          >
            Run full sync
          </button>
        </div>
      </dialog>
    </main>
  );
}

function ConnectionCard({ icon, title, subtitle, onTest, loading, disabled }) {
  return (
    <div className="connection-card">
      <div className="connection-icon">{icon}</div>
      <div className="connection-copy">
        <strong>{title}</strong>
        <span>{subtitle}</span>
      </div>
      <span className="connected-label">
        <span className="status-dot" /> Ready
      </span>
      <button className="secondary-button" onClick={onTest} disabled={disabled}>
        {loading ? (
          <LoaderCircle className="spin" size={16} />
        ) : (
          "Test connection"
        )}
      </button>
    </div>
  );
}
function MetricCard({ icon, label, value, tone }) {
  return (
    <div className={`metric-card ${tone}`}>
      <span className="metric-icon">{icon}</span>
      <span className="metric-label">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
function PanelHeading({ icon, title, subtitle }) {
  return (
    <div className="panel-heading">
      <span className="heading-icon">{icon}</span>
      <div>
        <h3>{title}</h3>
        <p>{subtitle}</p>
      </div>
    </div>
  );
}
function ActionButton({ icon, label, onClick, primary, disabled, loading }) {
  return (
    <button
      className={
        primary
          ? "primary-button action-button"
          : "secondary-button action-button"
      }
      onClick={onClick}
      disabled={disabled}
    >
      {loading ? <LoaderCircle className="spin" size={17} /> : icon}
      <span>{label}</span>
    </button>
  );
}
function DataPanel({ title, subtitle, icon, children }) {
  return (
    <div className="panel data-panel">
      <PanelHeading icon={icon} title={title} subtitle={subtitle} />
      {children}
    </div>
  );
}
function LedgerDetailsPanel({ details, error, loading, onClose, onRetry }) {
  return (
    <section className="panel ledger-details-panel" aria-live="polite">
      <div className="details-header">
        <PanelHeading
          icon={<BookOpen />}
          title={details ? details.name : "Ledger details"}
          subtitle="Synchronized MySQL record and related transactions"
        />
        <button className="secondary-button" type="button" onClick={onClose}>
          Back to ledgers
        </button>
      </div>

      {loading && (
        <div className="details-loading">
          <LoaderCircle className="spin" size={19} /> Loading ledger details…
        </div>
      )}

      {!loading && error && (
        <div className="details-error notice error">
          <CircleAlert size={17} />
          <span>{error}</span>
          <button className="secondary-button" type="button" onClick={onRetry}>
            Retry
          </button>
        </div>
      )}

      {!loading && !error && details && (
        <>
          <div className="ledger-meta-grid">
            <DetailValue label="Ledger ID" value={details.id} />
            <DetailValue label="Parent" value={details.parent || "—"} />
            <DetailValue
              label="Created at"
              value={formatDateTime(details.created_at)}
            />
            <DetailValue
              label="Updated at"
              value={formatDateTime(details.updated_at)}
            />
          </div>
          <div className="details-subheading">
            <div>
              <h4>Related transactions</h4>
              <p>{details.transactions.length} transaction records</p>
            </div>
          </div>
          {details.transactions.length === 0 ? (
            <p className="empty-details">
              No transactions found for this ledger.
            </p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Voucher type</th>
                    <th>Voucher number</th>
                    <th>Narration</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {details.transactions.map((transaction) => (
                    <tr
                      key={`${transaction.voucher_id}-${transaction.voucher_number}`}
                    >
                      <td className="strong-cell">
                        {formatDate(transaction.voucher_date)}
                      </td>
                      <td>{transaction.voucher_type || "—"}</td>
                      <td>{transaction.voucher_number || "—"}</td>
                      <td className="truncate">
                        {transaction.narration || "—"}
                      </td>
                      <td className="amount-cell">{transaction.amount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
function DetailValue({ label, value }) {
  return (
    <div className="detail-value">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
function LoadingRows({ columns }) {
  return Array.from({ length: 3 }, (_, index) => (
    <tr key={index} className="loading-row">
      <td colSpan={columns}>
        <span />
      </td>
    </tr>
  ));
}
function EmptyRow({ columns, text }) {
  return (
    <tr>
      <td colSpan={columns} className="empty-cell">
        {text}
      </td>
    </tr>
  );
}

export default App;
