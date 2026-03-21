export interface AppointmentModel {
  dateTime: string;
  duration: number;
  type: 'checkup' | 'follow_up' | 'emergency' | 'consultation';
  notes?: string;
}
