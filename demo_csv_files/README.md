# Demo CSV Files for FlexiFund Transaction Import

This directory contains sample bank statement CSV files in various formats to test the FlexiFund transaction import functionality.

## Available CSV Files

### 1. **sbi_format.csv** - SBI Bank Format
- **Columns**: Txn Date, Description, Dr, Cr, Balance, Ref No, Channel
- **Transactions**: 20 entries
- **Features**: 
  - Mix of salary, expenses, and gig economy earnings
  - Includes work-related expenses (fuel, vehicle service)
  - Various payment modes (UPI, NEFT, POS, DC)

### 2. **hdfc_format.csv** - HDFC Bank Format
- **Columns**: Transaction Date, Narration, Amount Debited, Amount Credited, Closing Balance, Reference No, Transaction Mode
- **Transactions**: 19 entries
- **Features**:
  - Date format: DD-MM-YYYY
  - Includes freelance consulting income
  - Self-transfers and bill payments

### 3. **standard_bank_statement.csv** - Generic Bank Format
- **Columns**: Date, Description, Debit, Credit, Balance
- **Transactions**: 20 entries
- **Features**:
  - Simple, clean format
  - Common transaction types
  - Easy to read and understand

### 4. **single_amount_column.csv** - Amount-Based Format
- **Columns**: Date, Particulars, Transaction Amount, Available Balance, Transaction ID, Payment Mode
- **Transactions**: 21 entries
- **Features**:
  - Uses negative/positive amounts instead of separate debit/credit columns
  - Date format: YYYY-MM-DD
  - Includes payment mode information

### 5. **delivery_rider_statement.csv** - Delivery Rider Focused
- **Columns**: Date, Description, Debit, Credit, Balance, Reference, Mode
- **Transactions**: 21 entries
- **Features**:
  - Realistic delivery rider income (Zomato, Swiggy, Dunzo payouts)
  - Work expenses (fuel, vehicle maintenance, commercial permits)
  - Lower income bracket with essential expenses
  - Work-related classifications

### 6. **icici_format.csv** - ICICI Bank Format
- **Columns**: Value Date, Transaction, Debit, Credit, Balance, Cheque Number, Mode
- **Transactions**: 22 entries
- **Features**:
  - Date format: YYYY-MM-DD
  - Includes education expenses (Coursera)
  - Insurance premiums
  - Consulting income

## Transaction Categories Covered

Each CSV file includes realistic examples of:

### Income
- ✅ Salary payments
- ✅ Freelance/consulting income
- ✅ Gig economy earnings (delivery platforms)
- ✅ Client payments

### Expenses
- 🍔 **Food**: Swiggy, Zomato, restaurants, cafes
- 🏠 **Rent**: Monthly rent payments
- 🚗 **Transportation**: Fuel (HP, Indian Oil, IOCL, Bharat Petroleum), Uber, Ola, Rapido, Metro
- ⚡ **Utilities**: Electricity, water, broadband/internet bills
- 💳 **EMI & Loans**: Insurance premiums
- 🏥 **Healthcare**: Pharmacy, hospital visits
- 🎓 **Education**: Online courses (Udemy, Coursera)
- 🎬 **Entertainment**: Netflix, Spotify, Disney Hotstar
- 🛒 **Shopping**: Amazon, Flipkart, Myntra

### Work-Related Expenses (for Delivery Riders)
- ⛽ Fuel costs (marked as work expenses)
- 🔧 Vehicle maintenance and repairs
- 🛡️ Commercial vehicle permits
- 📱 Mobile data recharges
- 🚴 Vehicle parts (tyres, chains, brakes)

### Transfers
- 💰 Self-transfers to savings accounts
- 💼 Own account transfers

## Testing Different Scenarios

### Column Mapping Test
The system should automatically detect and map columns like:
- Date columns: "Date", "Txn Date", "Transaction Date", "Value Date"
- Debit columns: "Dr", "Debit", "Amount Debited"
- Credit columns: "Cr", "Credit", "Amount Credited"
- Balance columns: "Balance", "Closing Balance", "Available Balance"
- Reference columns: "Ref No", "Reference No", "Transaction ID"

### Classification Test
The AI should correctly classify:
- ✅ Income transactions (salary, freelance, gig earnings)
- ✅ Essential expenses (rent, utilities, food, healthcare)
- ✅ Non-essential expenses (entertainment, shopping)
- ✅ Work expenses (fuel, vehicle maintenance for riders)
- ✅ Transfers (self-transfers, own account)

### Edge Cases
- Negative amounts in single-amount column format
- Different date formats (DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY)
- Missing payment modes or reference numbers
- Similar merchants on same day (duplicate detection)

## How to Use

1. Start the FlexiFund backend and frontend
2. Log in to your account
3. Navigate to "Import Transactions" or "Bank Statement Import"
4. Upload any of these CSV files
5. Review the automatic classification
6. Correct any misclassifications to train the system

## Expected Behavior

- **Preview**: Shows first 50 transactions with classifications
- **Auto-Classification**: Automatically categorizes based on description patterns
- **Confidence Levels**: High/Medium/Low based on pattern matching
- **Review Flags**: Some transactions marked for manual review
- **Duplicate Detection**: Skips duplicate transactions based on fingerprinting
- **Work Expense Detection**: Platform fees, fuel, and vehicle costs marked for riders

## Notes

- All data is synthetic and for testing purposes only
- Dates are set to November 2026
- Amounts and descriptions are realistic but fictional
- The system learns from your corrections for future imports
