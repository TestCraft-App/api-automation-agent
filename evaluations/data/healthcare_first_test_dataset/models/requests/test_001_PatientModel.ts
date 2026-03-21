export interface EmergencyContact {
  name: string;
  phone: string;
  relationship?: string;
}

export interface PatientModel {
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  gender: 'male' | 'female' | 'other' | 'prefer_not_to_say';
  allergies?: string[];
  emergencyContact?: EmergencyContact;
}
