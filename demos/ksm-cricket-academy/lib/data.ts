export type Constituency = {
  id: string;
  name: string;
  districts: string[];
};

export const CONSTITUENCIES: Constituency[] = [
  { id: 'north', name: 'North Zone', districts: ['Agra', 'Mathura', 'Aligarh', 'Etah'] },
  { id: 'south', name: 'South Zone', districts: ['Mysore', 'Mandya', 'Chamrajnagar', 'Hassan'] },
  { id: 'east', name: 'East Zone', districts: ['Patna', 'Gaya', 'Muzaffarpur', 'Bhagalpur'] },
  { id: 'west', name: 'West Zone', districts: ['Surat', 'Vadodara', 'Rajkot', 'Junagadh'] },
  { id: 'central', name: 'Central Zone', districts: ['Bhopal', 'Indore', 'Gwalior', 'Jabalpur'] },
];

export type Member = {
  id: string;
  name: string;
  age: number;
  village: string;
  district: string;
  constituency: string;
  phone: string;
  joinDate: string;
  status: 'active' | 'inactive';
  membershipNo: string;
};

export const MOCK_MEMBERS: Member[] = [
  { id: '1', name: 'Ravi Kumar', age: 18, village: 'Rampur', district: 'Agra', constituency: 'north', phone: '9876543210', joinDate: '2024-01-15', status: 'active', membershipNo: 'KSM-0001' },
  { id: '2', name: 'Suresh Reddy', age: 22, village: 'Kollur', district: 'Mysore', constituency: 'south', phone: '9876543211', joinDate: '2024-01-20', status: 'active', membershipNo: 'KSM-0002' },
  { id: '3', name: 'Pradeep Singh', age: 19, village: 'Bichpuri', district: 'Agra', constituency: 'north', phone: '9876543212', joinDate: '2024-02-01', status: 'active', membershipNo: 'KSM-0003' },
  { id: '4', name: 'Arjun Sharma', age: 25, village: 'Karhal', district: 'Mathura', constituency: 'north', phone: '9876543213', joinDate: '2024-02-10', status: 'active', membershipNo: 'KSM-0004' },
  { id: '5', name: 'Vikram Nair', age: 21, village: 'Piriyapatna', district: 'Mysore', constituency: 'south', phone: '9876543214', joinDate: '2024-02-15', status: 'active', membershipNo: 'KSM-0005' },
  { id: '6', name: 'Rajesh Yadav', age: 17, village: 'Fatehpur Sikri', district: 'Agra', constituency: 'north', phone: '9876543215', joinDate: '2024-03-01', status: 'active', membershipNo: 'KSM-0006' },
  { id: '7', name: 'Mohan Das', age: 20, village: 'Bodh Gaya', district: 'Gaya', constituency: 'east', phone: '9876543216', joinDate: '2024-03-10', status: 'active', membershipNo: 'KSM-0007' },
  { id: '8', name: 'Sanjay Patel', age: 23, village: 'Ankleshwar', district: 'Surat', constituency: 'west', phone: '9876543217', joinDate: '2024-03-15', status: 'active', membershipNo: 'KSM-0008' },
  { id: '9', name: 'Anil Tiwari', age: 16, village: 'Vidisha', district: 'Bhopal', constituency: 'central', phone: '9876543218', joinDate: '2024-04-01', status: 'active', membershipNo: 'KSM-0009' },
  { id: '10', name: 'Rahul Mishra', age: 24, village: 'Sanchi', district: 'Bhopal', constituency: 'central', phone: '9876543219', joinDate: '2024-04-05', status: 'active', membershipNo: 'KSM-0010' },
  { id: '11', name: 'Deepak Verma', age: 18, village: 'Hathras', district: 'Aligarh', constituency: 'north', phone: '9876543220', joinDate: '2024-04-12', status: 'active', membershipNo: 'KSM-0011' },
  { id: '12', name: 'Kishore Gupta', age: 26, village: 'Nalanda', district: 'Patna', constituency: 'east', phone: '9876543221', joinDate: '2024-04-20', status: 'active', membershipNo: 'KSM-0012' },
  { id: '13', name: 'Ramesh Joshi', age: 19, village: 'Ooty', district: 'Mysore', constituency: 'south', phone: '9876543222', joinDate: '2024-05-01', status: 'inactive', membershipNo: 'KSM-0013' },
  { id: '14', name: 'Govind Rao', age: 22, village: 'Ujjain', district: 'Indore', constituency: 'central', phone: '9876543223', joinDate: '2024-05-08', status: 'active', membershipNo: 'KSM-0014' },
  { id: '15', name: 'Harish Chandra', age: 20, village: 'Vaishali', district: 'Muzaffarpur', constituency: 'east', phone: '9876543224', joinDate: '2024-05-15', status: 'active', membershipNo: 'KSM-0015' },
  { id: '16', name: 'Sunil Dhingra', age: 21, village: 'Anand', district: 'Vadodara', constituency: 'west', phone: '9876543225', joinDate: '2024-05-22', status: 'active', membershipNo: 'KSM-0016' },
  { id: '17', name: 'Pankaj Dubey', age: 23, village: 'Chitrakoot', district: 'Jabalpur', constituency: 'central', phone: '9876543226', joinDate: '2024-06-01', status: 'active', membershipNo: 'KSM-0017' },
  { id: '18', name: 'Ajay Rawat', age: 17, village: 'Junagadh Town', district: 'Junagadh', constituency: 'west', phone: '9876543227', joinDate: '2024-06-10', status: 'active', membershipNo: 'KSM-0018' },
  { id: '19', name: 'Manoj Pillai', age: 25, village: 'Belur', district: 'Hassan', constituency: 'south', phone: '9876543228', joinDate: '2024-06-15', status: 'inactive', membershipNo: 'KSM-0019' },
  { id: '20', name: 'Dinesh Babu', age: 19, village: 'Sasaram', district: 'Bhagalpur', constituency: 'east', phone: '9876543229', joinDate: '2024-06-20', status: 'active', membershipNo: 'KSM-0020' },
];

export type Tournament = {
  id: string;
  name: string;
  date: string;
  location: string;
  level: 'village' | 'district' | 'state';
  status: 'upcoming' | 'ongoing' | 'completed';
  teams: number;
};

export const TOURNAMENTS: Tournament[] = [
  {
    id: '1',
    name: 'Village Cup 2025',
    date: '2025-03-10',
    location: 'KSM Village Ground, Rampur',
    level: 'village',
    status: 'upcoming',
    teams: 8,
  },
  {
    id: '2',
    name: 'District Championship',
    date: '2025-05-15',
    location: 'District Sports Complex',
    level: 'district',
    status: 'upcoming',
    teams: 16,
  },
  {
    id: '3',
    name: 'KSM State Trophy',
    date: '2025-07-20',
    location: 'State Cricket Ground',
    level: 'state',
    status: 'upcoming',
    teams: 32,
  },
];

export const GALLERY_IMAGES = [
  { id: '1', seed: 'ksm-cricket-training-1', category: 'training', caption: 'Morning training session', width: 800, height: 600 },
  { id: '2', seed: 'ksm-cricket-match-2', category: 'tournaments', caption: 'District Championship finals', width: 800, height: 600 },
  { id: '3', seed: 'ksm-cricket-camp-3', category: 'events', caption: 'Annual cricket camp', width: 800, height: 600 },
  { id: '4', seed: 'ksm-cricket-training-4', category: 'training', caption: 'Batting drills', width: 800, height: 600 },
  { id: '5', seed: 'ksm-cricket-match-5', category: 'tournaments', caption: 'Village Cup 2024', width: 800, height: 600 },
  { id: '6', seed: 'ksm-cricket-award-6', category: 'events', caption: 'Award ceremony', width: 800, height: 600 },
  { id: '7', seed: 'ksm-cricket-field-7', category: 'training', caption: 'Ground preparation', width: 800, height: 600 },
  { id: '8', seed: 'ksm-cricket-team-8', category: 'tournaments', caption: 'State Trophy team photo', width: 800, height: 600 },
  { id: '9', seed: 'ksm-cricket-kids-9', category: 'events', caption: 'Junior coaching session', width: 800, height: 600 },
  { id: '10', seed: 'ksm-cricket-bowling-10', category: 'training', caption: 'Bowling practice', width: 800, height: 600 },
  { id: '11', seed: 'ksm-cricket-crowd-11', category: 'tournaments', caption: 'Opening ceremony', width: 800, height: 600 },
  { id: '12', seed: 'ksm-cricket-trophy-12', category: 'events', caption: 'Trophy presentation', width: 800, height: 600 },
];
