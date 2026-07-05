import React, { useState, useEffect, useRef } from 'react';

// Backend Endpoint (configured to Django API on port 8005)
const API_BASE = 'http://localhost:8005/api';

function App() {
  // Auth state
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [user, setUser] = useState(null);
  const [isRegistering, setIsRegistering] = useState(false);

  // Form states (auth)
  const [emailInput, setEmailInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [firstNameInput, setFirstNameInput] = useState('');
  const [lastNameInput, setLastNameInput] = useState('');

  // Dashboard state
  const [wallets, setWallets] = useState([]);
  const [activeWallet, setActiveWallet] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard', 'transactions', 'admin'

  // Transactions state
  const [transactions, setTransactions] = useState([]);
  const [txPage, setTxPage] = useState(1);
  const [txCount, setTxCount] = useState(0);
  const [txSearch, setTxSearch] = useState('');
  const [hasMoreTx, setHasMoreTx] = useState(false);

  // Modals state
  const [modalType, setModalType] = useState(null); // 'deposit', 'withdraw', 'transfer', 'create_wallet'
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [recipientEmail, setRecipientEmail] = useState('');
  const [recipientWalletId, setRecipientWalletId] = useState('');
  const [newWalletName, setNewWalletName] = useState('Savings Wallet');
  const [newWalletCurrency, setNewWalletCurrency] = useState('NGN');

  // Autocomplete suggestions
  const [searchQuery, setSearchQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isSearchingUser, setIsSearchingUser] = useState(false);

  // Admin states
  const [adminStats, setAdminStats] = useState(null);
  const [adminWallets, setAdminWallets] = useState([]);
  const [adminTransactions, setAdminTransactions] = useState([]);
  const [adminWalletsPage, setAdminWalletsPage] = useState(1);
  const [adminTxPage, setAdminTxPage] = useState(1);
  const [adminWalletsCount, setAdminWalletsCount] = useState(0);
  const [adminTxCount, setAdminTxCount] = useState(0);
  const [adminSearchQuery, setAdminSearchQuery] = useState('');

  // Notifications
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Run initial profile check on mount/token load
  useEffect(() => {
    if (token) {
      localStorage.setItem('token', token);
      fetchProfile();
    } else {
      localStorage.removeItem('token');
      setUser(null);
    }
  }, [token]);

  // Load wallets once logged in
  useEffect(() => {
    if (user) {
      fetchWallets();
    }
  }, [user]);

  // Fetch transaction logs when active wallet, page, or search query changes
  useEffect(() => {
    if (user && activeWallet) {
      fetchTransactions(activeWallet.id, txPage, txSearch);
    }
  }, [user, activeWallet, txPage, txSearch]);

  // Fetch admin dashboard lists
  useEffect(() => {
    if (user?.is_staff && activeTab === 'admin') {
      fetchAdminStats();
      fetchAdminWallets(adminWalletsPage, adminSearchQuery);
      fetchAdminTransactions(adminTxPage, adminSearchQuery);
    }
  }, [user, activeTab, adminWalletsPage, adminTxPage, adminSearchQuery]);

  // Search autocomplete recipient debounce
  useEffect(() => {
    if (recipientEmail.length > 2) {
      const delayDebounceFn = setTimeout(() => {
        lookupRecipient(recipientEmail);
      }, 300);
      return () => clearTimeout(delayDebounceFn);
    } else {
      setSuggestions([]);
    }
  }, [recipientEmail]);

  const apiHeaders = (extra = {}) => ({
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...extra
  });

  const fetchProfile = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/me/`, { headers: apiHeaders() });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        handleLogout();
      }
    } catch (e) {
      showToast('Connection to server failed', 'error');
    }
  };

  const fetchWallets = async () => {
    try {
      const res = await fetch(`${API_BASE}/wallets/`, { headers: apiHeaders() });
      if (res.ok) {
        const data = await res.json();
        setWallets(data);
        if (data.length > 0 && !activeWallet) {
          setActiveWallet(data[0]);
        } else if (data.length > 0 && activeWallet) {
          // Refresh active wallet details
          const current = data.find(w => w.id === activeWallet.id);
          if (current) setActiveWallet(current);
        }
      }
    } catch (e) {
      showToast('Failed to fetch wallets', 'error');
    }
  };

  const fetchTransactions = async (walletId, page, search) => {
    try {
      const res = await fetch(`${API_BASE}/wallets/${walletId}/history/?page=${page}&search=${search}`, {
        headers: apiHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        // Check if paginated or normal array
        if (data.results !== undefined) {
          setTransactions(data.results);
          setTxCount(data.count);
          setHasMoreTx(data.next !== null);
        } else {
          setTransactions(data);
          setTxCount(data.length);
          setHasMoreTx(false);
        }
      }
    } catch (e) {
      showToast('Failed to fetch transactions', 'error');
    }
  };

  const lookupRecipient = async (query) => {
    setIsSearchingUser(true);
    try {
      const res = await fetch(`${API_BASE}/users/?search=${query}`, { headers: apiHeaders() });
      if (res.ok) {
        const data = await res.json();
        // Suggestions will contain user objects. Each user has wallets.
        // We will fetch user wallets to get recipient wallet ID.
        // But since standard user endpoint returns just user info, let's list their email,
        // and fetch their NGN wallet when selected, or let the user paste recipient wallet ID.
        // Wait, to make it frictionless, when a user is selected from suggestions, we query their NGN wallet.
        // Let's store suggestions.
        setSuggestions(data.results || data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsSearchingUser(false);
    }
  };

  // Auth Handlers
  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/auth/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: emailInput, password: passwordInput })
      });
      const data = await res.json();
      if (res.ok) {
        setToken(data.access);
        showToast('Successfully logged in!');
      } else {
        showToast(data.detail || 'Authentication failed', 'error');
      }
    } catch (e) {
      showToast('Network error during login', 'error');
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/auth/register/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: emailInput,
          password: passwordInput,
          first_name: firstNameInput,
          last_name: lastNameInput
        })
      });
      const data = await res.json();
      if (res.ok) {
        setToken(data.tokens.access);
        showToast('Account registered successfully!');
        setIsRegistering(false);
      } else {
        showToast(Object.values(data).join(', ') || 'Registration failed', 'error');
      }
    } catch (e) {
      showToast('Network error during registration', 'error');
    }
  };

  const handleLogout = () => {
    setToken('');
    setUser(null);
    setWallets([]);
    setActiveWallet(null);
    setTransactions([]);
    localStorage.removeItem('token');
    showToast('Logged out successfully');
  };

  // Transaction Actions
  const handleDeposit = async (e) => {
    e.preventDefault();
    const idempotencyKey = uuidv4();
    try {
      const res = await fetch(`${API_BASE}/transactions/deposit/`, {
        method: 'POST',
        headers: apiHeaders({ 'X-Idempotency-Key': idempotencyKey }),
        body: JSON.stringify({
          wallet_id: activeWallet.id,
          amount: parseFloat(amount).toFixed(4),
          description: description
        })
      });
      const data = await res.json();
      if (res.ok) {
        showToast(`Funded wallet with ${amount} ${activeWallet.currency}`);
        setModalType(null);
        resetForm();
        fetchWallets();
      } else {
        showToast(data.error || 'Deposit failed', 'error');
      }
    } catch (e) {
      showToast('Transaction error', 'error');
    }
  };

  const handleWithdraw = async (e) => {
    e.preventDefault();
    const idempotencyKey = uuidv4();
    try {
      const res = await fetch(`${API_BASE}/transactions/withdraw/`, {
        method: 'POST',
        headers: apiHeaders({ 'X-Idempotency-Key': idempotencyKey }),
        body: JSON.stringify({
          wallet_id: activeWallet.id,
          amount: parseFloat(amount).toFixed(4),
          description: description
        })
      });
      const data = await res.json();
      if (res.ok) {
        showToast(`Withdrew ${amount} ${activeWallet.currency}`);
        setModalType(null);
        resetForm();
        fetchWallets();
      } else {
        showToast(data.error || 'Withdrawal failed', 'error');
      }
    } catch (e) {
      showToast('Transaction error', 'error');
    }
  };

  const handleTransfer = async (e) => {
    e.preventDefault();
    if (!recipientWalletId) {
      showToast('Please select a valid recipient with a wallet', 'error');
      return;
    }
    const idempotencyKey = uuidv4();
    try {
      const res = await fetch(`${API_BASE}/transactions/transfer/`, {
        method: 'POST',
        headers: apiHeaders({ 'X-Idempotency-Key': idempotencyKey }),
        body: JSON.stringify({
          source_wallet_id: activeWallet.id,
          destination_wallet_id: recipientWalletId,
          amount: parseFloat(amount).toFixed(4),
          description: description
        })
      });
      const data = await res.json();
      if (res.ok) {
        showToast(`Transferred ${amount} ${activeWallet.currency} successfully!`);
        setModalType(null);
        resetForm();
        fetchWallets();
      } else {
        showToast(data.error || Object.values(data).join(', ') || 'Transfer failed', 'error');
      }
    } catch (e) {
      showToast('Transaction error', 'error');
    }
  };

  const handleCreateWallet = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/wallets/`, {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({
          name: newWalletName,
          currency: newWalletCurrency.toUpperCase()
        })
      });
      const data = await res.json();
      if (res.ok) {
        showToast(`Created wallet: ${newWalletName}`);
        setModalType(null);
        fetchWallets();
      } else {
        showToast(data.non_field_errors?.[0] || 'Failed to create wallet', 'error');
      }
    } catch (e) {
      showToast('Create wallet error', 'error');
    }
  };

  // Admin API Handlers
  const fetchAdminStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/admin/dashboard/`, { headers: apiHeaders() });
      if (res.ok) {
        const data = await res.json();
        setAdminStats(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAdminWallets = async (page, search) => {
    try {
      const res = await fetch(`${API_BASE}/admin/wallets/?page=${page}&search=${search}`, { headers: apiHeaders() });
      if (res.ok) {
        const data = await res.json();
        setAdminWallets(data.results || []);
        setAdminWalletsCount(data.count || 0);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAdminTransactions = async (page, search) => {
    try {
      const res = await fetch(`${API_BASE}/admin/transactions/?page=${page}&search=${search}`, { headers: apiHeaders() });
      if (res.ok) {
        const data = await res.json();
        setAdminTransactions(data.results || []);
        setAdminTxCount(data.count || 0);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Helper UUID function
  const uuidv4 = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = (Math.random() * 16) | 0,
        v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  };

  const resetForm = () => {
    setAmount('');
    setDescription('');
    setRecipientEmail('');
    setRecipientWalletId('');
    setSuggestions([]);
  };

  // Select suggestion helper
  const handleSelectRecipientUser = async (recipient) => {
    setRecipientEmail(recipient.email);
    setSuggestions([]);
    
    // Fetch recipient wallets to find one matching activeWallet currency
    try {
      // In a real app, we query recipient wallets.
      // For this implementation, we will perform a quick check
      // since the suggestions object lists user details. Let's look up wallets
      // through a custom flow or paste. To make W2W lookup fully functional,
      // let's fetch recipient's wallet of corresponding currency.
      // We can query a list of wallets, but standard users can't list another user's wallets.
      // BUT they can retrieve it if the UserListView response (or suggestions) returned it.
      // Wait, let's update User Search endpoint to return user's wallet IDs of matching currency!
      // In UserListView, we only returned basic User info. Let's make sure the suggestions
      // helper works. Let's query matching wallet if it's there.
      // Wait! If the user search includes a list of wallets, that makes autocomplete fully resolved.
      // Let's modify UserSearch view to include the wallet IDs!
      // Wait, does the API return matching wallet? Let's check how we can fetch it.
      // If not, we can let them input it or query it. Let's implement UserSerializer
      // to return user's wallets!
      // Let's check if UserSerializer can include wallets: yes, UserSerializer has access to wallets.
      // Let's update user/serializers.py to list wallets. Let's do that next.
      // For now, if user has wallets in the suggestion, select the first matching currency wallet.
      // If we serializer wallets inside UserSerializer, then `recipient.wallets` will contain them.
      // Let's select the wallet:
      const match = recipient.wallets?.find(w => w.currency === activeWallet.currency);
      if (match) {
        setRecipientWalletId(match.id);
      } else {
        // Fallback: search for any NGN wallet or allow pasting
        showToast(`No wallet found for recipient in currency ${activeWallet.currency}`, 'error');
      }
    } catch (e) {
      showToast('Error selecting recipient', 'error');
    }
  };

  if (!token) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-logo">Antigravity Wallet</div>
          <div className="auth-subtitle">High Performance Fintech Ledger</div>

          <form onSubmit={isRegistering ? handleRegister : handleLogin}>
            {isRegistering && (
              <>
                <div className="form-group">
                  <label className="form-label">First Name</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Alice"
                    value={firstNameInput}
                    onChange={e => setFirstNameInput(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Last Name</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Liddell"
                    value={lastNameInput}
                    onChange={e => setLastNameInput(e.target.value)}
                    required
                  />
                </div>
              </>
            )}

            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input
                type="email"
                className="form-control"
                placeholder="email@example.com"
                value={emailInput}
                onChange={e => setEmailInput(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                type="password"
                className="form-control"
                placeholder="••••••••"
                value={passwordInput}
                onChange={e => setPasswordInput(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="btn-primary">
              {isRegistering ? 'Create Account' : 'Sign In'}
            </button>
          </form>

          <button
            className="btn-tab btn-link"
            onClick={() => setIsRegistering(!isRegistering)}
          >
            {isRegistering ? 'Already have an account? Sign In' : 'New here? Register Account'}
          </button>
        </div>
        {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <header className="app-header">
        <div className="header-brand" onClick={() => setActiveTab('dashboard')}>
          Antigravity Wallet
        </div>
        <div className="header-menu">
          <button
            className={`btn-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            Dashboard
          </button>
          <button
            className={`btn-tab ${activeTab === 'transactions' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('transactions');
              setTxPage(1);
            }}
          >
            History
          </button>
          {user?.is_staff && (
            <button
              className={`btn-tab ${activeTab === 'admin' ? 'active' : ''}`}
              onClick={() => setActiveTab('admin')}
            >
              Admin Panel
            </button>
          )}

          <div className={`user-badge ${user?.is_staff ? 'admin' : ''}`}>
            {user?.email} {user?.is_staff ? '(Admin)' : ''}
          </div>
          <button className="btn-secondary" onClick={handleLogout}>
            Sign Out
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="dashboard-main">
        {/* Tab 1: Dashboard */}
        {activeTab === 'dashboard' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <h2 style={{ fontSize: '28px', fontWeight: '700' }}>Your Wallets</h2>
              <button className="btn-primary" style={{ width: 'auto' }} onClick={() => setModalType('create_wallet')}>
                + New Wallet
              </button>
            </div>

            {/* Wallets Cards Grid */}
            <div className="wallets-container">
              {wallets.map(w => (
                <div
                  key={w.id}
                  className={`wallet-card ${activeWallet?.id === w.id ? 'active' : ''}`}
                  onClick={() => setActiveWallet(w)}
                >
                  <div className="wallet-header">
                    <span className="wallet-title">{w.name}</span>
                    <span className="wallet-currency-badge">{w.currency}</span>
                  </div>
                  <div className="wallet-balance">
                    {parseFloat(w.balance).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <div className="wallet-actions" onClick={e => e.stopPropagation()}>
                    <button className="btn-secondary" onClick={() => { setActiveWallet(w); setModalType('deposit'); }}>
                      Deposit
                    </button>
                    <button className="btn-secondary" onClick={() => { setActiveWallet(w); setModalType('withdraw'); }}>
                      Withdraw
                    </button>
                    <button className="btn-primary" style={{ padding: '8px 12px', fontSize: '13px' }} onClick={() => { setActiveWallet(w); setModalType('transfer'); }}>
                      Send Money
                    </button>
                  </div>
                </div>
              ))}
              {wallets.length === 0 && (
                <div className="glass-card" style={{ gridColumn: '1/-1', textAlign: 'center', padding: '40px' }}>
                  <p style={{ color: 'var(--text-secondary)' }}>You don't own any wallets yet. Create one to begin!</p>
                </div>
              )}
            </div>

            {/* Active Wallet History Preview */}
            {activeWallet && (
              <div className="glass-card">
                <h3 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '20px' }}>
                  Recent Transactions for {activeWallet.name}
                </h3>
                <div className="data-table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Reference</th>
                        <th>Type</th>
                        <th>Description</th>
                        <th>Status</th>
                        <th>Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.slice(0, 5).map(tx => {
                        const isDebit = parseFloat(tx.amount) < 0;
                        return (
                          <tr key={tx.id}>
                            <td>{new Date(tx.created_at).toLocaleString()}</td>
                            <td style={{ fontFamily: 'monospace' }}>{tx.reference.substring(0, 15)}...</td>
                            <td>{tx.transaction_type}</td>
                            <td>{tx.description || '-'}</td>
                            <td>
                              <span className={`status-badge success`}>Success</span>
                            </td>
                            <td className={`amount-text ${isDebit ? 'debit' : 'credit'}`}>
                              {isDebit ? '' : '+'}{parseFloat(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })} {tx.currency}
                            </td>
                          </tr>
                        );
                      })}
                      {transactions.length === 0 && (
                        <tr>
                          <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '24px' }}>
                            No transaction history available.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Paginated History */}
        {activeTab === 'transactions' && activeWallet && (
          <div className="glass-card">
            <div className="table-header-row">
              <h2 style={{ fontSize: '24px', fontWeight: '700' }}>Transaction Ledger: {activeWallet.name}</h2>
              <div className="search-input-wrapper">
                <input
                  type="text"
                  className="form-control"
                  placeholder="Search reference/description..."
                  value={txSearch}
                  onChange={e => { setTxSearch(e.target.value); setTxPage(1); }}
                />
              </div>
            </div>

            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Reference ID</th>
                    <th>Type</th>
                    <th>Description</th>
                    <th>Status</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map(tx => {
                    const isDebit = parseFloat(tx.amount) < 0;
                    return (
                      <tr key={tx.id}>
                        <td>{new Date(tx.created_at).toLocaleString()}</td>
                        <td style={{ fontFamily: 'monospace' }}>{tx.reference}</td>
                        <td>{tx.transaction_type}</td>
                        <td>{tx.description || '-'}</td>
                        <td>
                          <span className={`status-badge success`}>Success</span>
                        </td>
                        <td className={`amount-text ${isDebit ? 'debit' : 'credit'}`}>
                          {isDebit ? '' : '+'}{parseFloat(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })} {tx.currency}
                        </td>
                      </tr>
                    );
                  })}
                  {transactions.length === 0 && (
                    <tr>
                      <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '40px' }}>
                        No records match the filter criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination controls */}
            <div className="pagination-container">
              <div className="pagination-info">
                Showing {transactions.length} records of {txCount} total
              </div>
              <div className="pagination-buttons">
                <button
                  className="btn-page"
                  disabled={txPage === 1}
                  onClick={() => setTxPage(p => Math.max(1, p - 1))}
                >
                  &lt;
                </button>
                <span className="btn-page" style={{ background: 'transparent', border: 'none', fontWeight: '600' }}>
                  {txPage}
                </span>
                <button
                  className="btn-page"
                  disabled={!hasMoreTx}
                  onClick={() => setTxPage(p => p + 1)}
                >
                  &gt;
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: System Admin Dashboard */}
        {activeTab === 'admin' && user?.is_staff && (
          <div>
            {/* Admin Stats cards */}
            <div className="stats-grid">
              <div className="stats-card">
                <span className="stats-label">Total Users</span>
                <span className="stats-value">{adminStats?.users_count || 0}</span>
              </div>
              <div className="stats-card">
                <span className="stats-label">Total Wallets</span>
                <span className="stats-value">{adminStats?.wallets_count || 0}</span>
              </div>
              <div className="stats-card">
                <span className="stats-label">Total System NGN Balance</span>
                <span className="stats-value" style={{ color: 'var(--accent-emerald)' }}>
                  ₦{parseFloat(adminStats?.total_ngn_balance || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </span>
              </div>
              <div className="stats-card">
                <span className="stats-label">Total Transactions</span>
                <span className="stats-value">{adminStats?.total_transactions || 0}</span>
              </div>
            </div>

            {/* Search filter for all lists */}
            <div className="glass-card" style={{ padding: '16px 24px', marginBottom: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-secondary)' }}>GLOBAL AUDIT FILTER</span>
                <input
                  type="text"
                  className="form-control"
                  style={{ maxWidth: '400px' }}
                  placeholder="Filter all tables by email, name, reference..."
                  value={adminSearchQuery}
                  onChange={e => {
                    setAdminSearchQuery(e.target.value);
                    setAdminWalletsPage(1);
                    setAdminTxPage(1);
                  }}
                />
              </div>
            </div>

            {/* All Wallets audit */}
            <div className="glass-card">
              <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px' }}>System Wallets Inventory</h3>
              <div className="data-table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Wallet ID</th>
                      <th>Owner Email</th>
                      <th>Label</th>
                      <th>Currency</th>
                      <th>Balance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {adminWallets.map(w => (
                      <tr key={w.id}>
                        <td style={{ fontFamily: 'monospace' }}>{w.id}</td>
                        <td style={{ fontWeight: '500' }}>{w.user_email || 'System User'}</td>
                        <td>{w.name}</td>
                        <td>{w.currency}</td>
                        <td style={{ fontWeight: '600' }}>
                          {parseFloat(w.balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* Wallets Pagination */}
              <div className="pagination-container">
                <div className="pagination-info">Total Wallets: {adminWalletsCount}</div>
                <div className="pagination-buttons">
                  <button
                    className="btn-page"
                    disabled={adminWalletsPage === 1}
                    onClick={() => setAdminWalletsPage(p => Math.max(1, p - 1))}
                  >
                    &lt;
                  </button>
                  <span className="btn-page" style={{ background: 'transparent', border: 'none' }}>{adminWalletsPage}</span>
                  <button
                    className="btn-page"
                    disabled={adminWalletsPage * 10 >= adminWalletsCount}
                    onClick={() => setAdminWalletsPage(p => p + 1)}
                  >
                    &gt;
                  </button>
                </div>
              </div>
            </div>

            {/* All Transactions audit */}
            <div className="glass-card">
              <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px' }}>System Transactions Audit Ledger</h3>
              <div className="data-table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Reference</th>
                      <th>Type</th>
                      <th>Amount</th>
                      <th>Status</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {adminTransactions.map(tx => (
                      <tr key={tx.id}>
                        <td>{new Date(tx.created_at).toLocaleString()}</td>
                        <td style={{ fontFamily: 'monospace' }}>{tx.reference}</td>
                        <td>{tx.transaction_type}</td>
                        <td style={{ fontWeight: '600' }}>
                          {parseFloat(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })} {tx.currency}
                        </td>
                        <td>
                          <span className="status-badge success">{tx.status}</span>
                        </td>
                        <td>{tx.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* Transactions Pagination */}
              <div className="pagination-container">
                <div className="pagination-info">Total Transactions: {adminTxCount}</div>
                <div className="pagination-buttons">
                  <button
                    className="btn-page"
                    disabled={adminTxPage === 1}
                    onClick={() => setAdminTxPage(p => Math.max(1, p - 1))}
                  >
                    &lt;
                  </button>
                  <span className="btn-page" style={{ background: 'transparent', border: 'none' }}>{adminTxPage}</span>
                  <button
                    className="btn-page"
                    disabled={adminTxPage * 10 >= adminTxCount}
                    onClick={() => setAdminTxPage(p => p + 1)}
                  >
                    &gt;
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Transaction Overlay Modals */}
      {modalType && (
        <div className="modal-overlay">
          <div className="modal-content">
            <button className="modal-close" onClick={() => setModalType(null)}>
              &times;
            </button>

            {modalType === 'deposit' && (
              <>
                <h3 className="modal-title">Deposit Funds</h3>
                <form onSubmit={handleDeposit}>
                  <div className="form-group">
                    <label className="form-label">Amount ({activeWallet?.currency})</label>
                    <input
                      type="number"
                      step="0.0001"
                      className="form-control"
                      placeholder="0.0000"
                      value={amount}
                      onChange={e => setAmount(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Description</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="e.g. Funding wallet"
                      value={description}
                      onChange={e => setDescription(e.target.value)}
                    />
                  </div>
                  <button type="submit" className="btn-primary">
                    Deposit
                  </button>
                </form>
              </>
            )}

            {modalType === 'withdraw' && (
              <>
                <h3 className="modal-title">Withdraw Funds</h3>
                <form onSubmit={handleWithdraw}>
                  <div className="form-group">
                    <label className="form-label">Amount ({activeWallet?.currency})</label>
                    <input
                      type="number"
                      step="0.0001"
                      className="form-control"
                      placeholder="0.0000"
                      value={amount}
                      onChange={e => setAmount(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Description</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="e.g. Withdrawal to bank"
                      value={description}
                      onChange={e => setDescription(e.target.value)}
                    />
                  </div>
                  <button type="submit" className="btn-primary">
                    Withdraw
                  </button>
                </form>
              </>
            )}

            {modalType === 'transfer' && (
              <>
                <h3 className="modal-title">Wallet-to-Wallet Transfer</h3>
                <form onSubmit={handleTransfer}>
                  <div className="form-group search-container">
                    <label className="form-label">Recipient Email</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Search recipient by email..."
                      value={recipientEmail}
                      onChange={e => {
                        setRecipientEmail(e.target.value);
                        setRecipientWalletId('');
                      }}
                      required
                    />
                    {isSearchingUser && (
                      <div style={{ position: 'absolute', right: '15px', top: '35px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                        Searching...
                      </div>
                    )}
                    {suggestions.length > 0 && (
                      <div className="suggestions-dropdown">
                        {suggestions.map(s => (
                          <div
                            key={s.id}
                            className="suggestion-item"
                            onClick={() => handleSelectRecipientUser(s)}
                          >
                            {s.first_name} {s.last_name} ({s.email})
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="form-group">
                    <label className="form-label">Recipient Wallet ID</label>
                    <input
                      type="text"
                      className="form-control"
                      style={{ fontFamily: 'monospace', fontSize: '13px' }}
                      placeholder="Will auto-fill or paste UUID..."
                      value={recipientWalletId}
                      onChange={e => setRecipientWalletId(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Amount ({activeWallet?.currency})</label>
                    <input
                      type="number"
                      step="0.0001"
                      className="form-control"
                      placeholder="0.0000"
                      value={amount}
                      onChange={e => setAmount(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Description</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="e.g. Lunch split"
                      value={description}
                      onChange={e => setDescription(e.target.value)}
                    />
                  </div>

                  <button type="submit" className="btn-primary">
                    Send Money
                  </button>
                </form>
              </>
            )}

            {modalType === 'create_wallet' && (
              <>
                <h3 className="modal-title">Create Wallet</h3>
                <form onSubmit={handleCreateWallet}>
                  <div className="form-group">
                    <label className="form-label">Wallet Name</label>
                    <input
                      type="text"
                      className="form-control"
                      value={newWalletName}
                      onChange={e => setNewWalletName(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Currency</label>
                    <select
                      className="form-control"
                      value={newWalletCurrency}
                      onChange={e => setNewWalletCurrency(e.target.value)}
                    >
                      <option value="NGN">NGN (₦)</option>
                      <option value="USD">USD ($)</option>
                      <option value="EUR">EUR (€)</option>
                      <option value="GBP">GBP (£)</option>
                    </select>
                  </div>
                  <button type="submit" className="btn-primary">
                    Create
                  </button>
                </form>
              </>
            )}
          </div>
        </div>
      )}

      {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}
    </div>
  );
}

export default App;
