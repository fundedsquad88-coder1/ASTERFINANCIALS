# Backend API notes

This service is a development/sandbox foundation. It provides market metadata, account registration/login, account lookup and trade-preview validation. It does not custody funds, execute real-money trades, or settle binary positions.

Before production: replace in-memory credentials with the database/ledger, use secure session storage, add rate limits and audit logging, connect an authoritative market-data provider, and implement jurisdiction-specific compliance and operational controls.
