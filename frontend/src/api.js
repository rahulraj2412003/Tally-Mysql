const request = async (path, options = {}) => {
  const response = await fetch(path, {
    headers: { Accept: "application/json", ...options.headers },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "The FastAPI service returned an error.");
  }
  return payload;
};

export const getLedgers = () => request("/api/ledgers");
export const getVouchers = () => request("/api/vouchers");
export const getVoucherEntries = () => request("/api/voucher-entries");
export const getSyncHistory = () => request("/api/sync/history");
export const getLedgerDetails = (ledgerId) =>
  request(`/api/ledgers/${ledgerId}`);
export const apiRequest = request;
