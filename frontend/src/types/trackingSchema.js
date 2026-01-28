/**
 * Auto-generated tracking schema for frontend form rendering.
 * Generated: 2026-01-27 21:18:14
 * Source: backend/api/tracking_routes.py
 *
 * DO NOT EDIT MANUALLY - run `jcodegen` to regenerate.
 */

// Stage field schemas for form rendering
export const STAGE_FIELDS = {
  applied: {
    datetime: { type: 'datetime', label: 'Date & Time' },
    type: { type: 'select', label: 'Type', options: ['online', 'referral'], default: 'online' },
    referrer_name: { type: 'text', label: 'Referrer Name', showIf: (data) => data.type === 'referral' },
    referrer_content: { type: 'text', label: 'Referral Details', showIf: (data) => data.type === 'referral' },
    note: { type: 'text', label: 'Note' },
  },
  screening: {
    datetime: { type: 'datetime', label: 'Date & Time' },
    type: { type: 'select', label: 'Type', options: ['phone', 'video'], default: 'phone' },
    with_person: { type: 'text', label: 'With' },
    note: { type: 'text', label: 'Note' },
  },
  interview: {
    datetime: { type: 'datetime', label: 'Date & Time' },
    round: { type: 'select', label: 'Round', options: ['1st', '2nd', '3rd', 'final'], default: '1st' },
    type: { type: 'select', label: 'Type', options: ['technical', 'behavioral', 'onsite'], default: 'technical' },
    interviewers: { type: 'text', label: 'Interviewers' },
    note: { type: 'text', label: 'Note' },
  },
  reference: {
    datetime: { type: 'datetime', label: 'Date & Time' },
    contacts_provided: { type: 'text', label: 'Contacts Provided' },
    note: { type: 'text', label: 'Note' },
  },
  offer: {
    datetime: { type: 'datetime', label: 'Date & Time' },
    amount: { type: 'text', label: 'Amount' },
    intention: { type: 'select', label: 'Intention', options: ['pending', 'leaning accept', 'leaning decline'] },
    note: { type: 'text', label: 'Note' },
  },
  rejected: {
    datetime: { type: 'datetime', label: 'Date & Time' },
    note: { type: 'text', label: 'Note' },
  },
};

// Job metadata fields (always editable)
export const METADATA_FIELDS = {
  salary: { type: 'text', label: 'Salary' },
  location: { type: 'text', label: 'Location' },
  general_note: { type: 'text', label: 'General Note' },
};
