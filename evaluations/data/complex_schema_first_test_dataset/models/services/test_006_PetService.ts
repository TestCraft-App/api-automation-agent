import { BaseService } from './BaseService.js';

interface PetModel {
  name: string;
  species: 'dog' | 'cat' | 'bird' | 'fish';
  age?: number;
  vaccinated?: boolean;
}

interface PetResponse {
  id: string;
  name: string;
  species: string;
  age?: number;
  vaccinated?: boolean;
}

export class PetService extends BaseService {
  async createPet<T = PetResponse>(pet: PetModel): Promise<T> {
    return this.post<T>('/pets', pet);
  }
}
