# Axis: Money

Load when the change computes, stores, converts or charges monetary amounts: prices, totals, balances, fees, tax, refunds, invoices, payments. Use with `review-angles.md`; units, integer division and precision across boundaries are in its Correctness section.

- Money in binary floating point (`float`, `double`, JS `number` used for amounts that are summed or compared). Check the type the project uses for money (integer minor units, `Decimal`, a money type) and that the new code keeps to it end to end, including parsing and serialization.
- Rounding: the mode (half-up, half-even, truncation) and *where* it happens. Rounding each line item and then summing gives a different total from summing and then rounding; tax, splits and currency conversion must follow the rule the domain sets.
- Currency: amounts in different currencies added or compared, or a currency's minor-unit count assumed to be 2 (JPY has 0, BHD has 3).
- Amount units at payment and accounting boundaries: a provider that takes minor units (cents) sent whole units, or the reverse. Read the provider's or ledger's definition of the field.
