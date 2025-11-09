"""
Mock LLM responses for integration testing.
These simulate realistic responses from the LLM for model and test generation.
"""

from src.ai_tools.models.model_file_spec import ModelFileSpec
from src.ai_tools.models.file_spec import FileSpec


MOCK_MODELS_RESPONSE = [
    ModelFileSpec(
        path="src/models/services/PetsService.ts",
        fileContent="""import { ApiBase } from '../../base/ApiBase';
import { Pet } from '../interfaces/Pet';
import { Pets } from '../interfaces/Pets';

export class PetsService extends ApiBase {
  async listPets(limit?: number): Promise<Pets> {
    const params = limit ? { limit } : {};
    return this.get('/pets', { params });
  }

  async createPets(pet: Pet): Promise<Pet> {
    return this.post('/pets', pet);
  }

  async showPetById(petId: string): Promise<Pet> {
    return this.get(`/pets/${petId}`);
  }
}
""",
        summary="PetsService service: listPets, createPets, showPetById",
    ),
    ModelFileSpec(
        path="src/models/interfaces/Pet.ts",
        fileContent="""export interface Pet {
  id: number;
  name: string;
  tag?: string;
}
""",
        summary="Pet model. Properties: id, name, tag",
    ),
    ModelFileSpec(
        path="src/models/interfaces/Pets.ts",
        fileContent="""import { Pet } from './Pet';

export type Pets = Pet[];
""",
        summary="Pets model. Properties: array of Pet",
    ),
    ModelFileSpec(
        path="src/models/interfaces/Error.ts",
        fileContent="""export interface Error {
  code: number;
  message: string;
}
""",
        summary="Error model. Properties: code, message",
    ),
]


MOCK_FIRST_TEST_GET_RESPONSE = [
    FileSpec(
        path="src/tests/pets/test_listPets.spec.ts",
        fileContent="""import { expect } from 'chai';
import { PetsService } from '../../models/services/PetsService';
import { Pets } from '../../models/interfaces/Pets';

describe('GET /pets - List all pets', () => {
  let petsService: PetsService;

  before(() => {
    petsService = new PetsService();
  });

  it('should return a list of pets', async () => {
    const response: Pets = await petsService.listPets();

    expect(response).to.be.an('array');
    expect(response.length).to.be.greaterThan(0);

    const pet = response[0];
    expect(pet).to.have.property('id');
    expect(pet).to.have.property('name');
    expect(pet.id).to.be.a('number');
    expect(pet.name).to.be.a('string');
  });

  it('should respect the limit parameter', async () => {
    const limit = 5;
    const response: Pets = await petsService.listPets(limit);

    expect(response).to.be.an('array');
    expect(response.length).to.be.at.most(limit);
  });

  it('should return proper error structure on failure', async () => {
    try {
      await petsService.listPets(-1);
      expect.fail('Should have thrown an error');
    } catch (error: any) {
      expect(error).to.have.property('code');
      expect(error).to.have.property('message');
    }
  });
});
""",
    )
]

MOCK_FIRST_TEST_POST_RESPONSE = [
    FileSpec(
        path="src/tests/pets/test_createPets.spec.ts",
        fileContent="""import { expect } from 'chai';
import { PetsService } from '../../models/services/PetsService';
import { Pet } from '../../models/interfaces/Pet';

describe('POST /pets - Create a pet', () => {
  let petsService: PetsService;

  before(() => {
    petsService = new PetsService();
  });

  it('should create a new pet', async () => {
    const newPet: Pet = {
      id: 0,
      name: 'Fluffy',
      tag: 'cat'
    };

    const response: Pet = await petsService.createPets(newPet);

    expect(response).to.be.an('object');
    expect(response).to.have.property('id');
    expect(response).to.have.property('name');
    expect(response.id).to.be.a('number');
    expect(response.id).to.be.greaterThan(0);
    expect(response.name).to.equal('Fluffy');
  });

  it('should fail when required fields are missing', async () => {
    const invalidPet = { tag: 'dog' } as Pet;

    try {
      await petsService.createPets(invalidPet);
      expect.fail('Should have thrown an error');
    } catch (error: any) {
      expect(error).to.have.property('code');
      expect(error).to.have.property('message');
    }
  });
});
""",
    )
]

MOCK_FIRST_TEST_GET_BY_ID_RESPONSE = [
    FileSpec(
        path="src/tests/pets/test_showPetById.spec.ts",
        fileContent="""import { expect } from 'chai';
import { PetsService } from '../../models/services/PetsService';
import { Pet } from '../../models/interfaces/Pet';

describe('GET /pets/{petId} - Show pet by ID', () => {
  let petsService: PetsService;

  before(() => {
    petsService = new PetsService();
  });

  it('should return a specific pet by ID', async () => {
    const petId = '1';
    const response: Pet = await petsService.showPetById(petId);

    expect(response).to.be.an('object');
    expect(response).to.have.property('id');
    expect(response).to.have.property('name');
    expect(response.id).to.equal(1);
    expect(response.name).to.be.a('string');
  });

  it('should return error for non-existent pet', async () => {
    const petId = '99999';

    try {
      await petsService.showPetById(petId);
      expect.fail('Should have thrown an error');
    } catch (error: any) {
      expect(error).to.have.property('code');
      expect(error.code).to.equal(404);
    }
  });
});
""",
    )
]


MOCK_ADDITIONAL_TESTS_RESPONSE = [
    FileSpec(
        path="src/tests/pets/test_listPets.spec.ts",
        fileContent="""import { expect } from 'chai';
import { PetsService } from '../../models/services/PetsService';
import { Pets } from '../../models/interfaces/Pets';

describe('GET /pets - List all pets', () => {
  let petsService: PetsService;

  before(() => {
    petsService = new PetsService();
  });

  it('should return a list of pets', async () => {
    const response: Pets = await petsService.listPets();

    expect(response).to.be.an('array');
    expect(response.length).to.be.greaterThan(0);

    const pet = response[0];
    expect(pet).to.have.property('id');
    expect(pet).to.have.property('name');
    expect(pet.id).to.be.a('number');
    expect(pet.name).to.be.a('string');
  });

  it('should respect the limit parameter', async () => {
    const limit = 5;
    const response: Pets = await petsService.listPets(limit);

    expect(response).to.be.an('array');
    expect(response.length).to.be.at.most(limit);
  });

  it('should return proper error structure on failure', async () => {
    try {
      await petsService.listPets(-1);
      expect.fail('Should have thrown an error');
    } catch (error: any) {
      expect(error).to.have.property('code');
      expect(error).to.have.property('message');
    }
  });

  it('should return empty array when no pets exist', async () => {
    const response: Pets = await petsService.listPets();
    expect(response).to.be.an('array');
  });

  it('should handle large limit values', async () => {
    const limit = 100;
    const response: Pets = await petsService.listPets(limit);

    expect(response).to.be.an('array');
    expect(response.length).to.be.at.most(limit);
  });
});
""",
    )
]


def get_mock_models_for_path(path: str):
    """Get mock model response based on the API path"""
    return MOCK_MODELS_RESPONSE


def get_mock_first_test_for_verb(path: str, verb: str):
    """Get mock first test response based on the API path and verb"""
    if verb.lower() == "get" and path == "/pets":
        return MOCK_FIRST_TEST_GET_RESPONSE
    elif verb.lower() == "post" and path == "/pets":
        return MOCK_FIRST_TEST_POST_RESPONSE
    elif verb.lower() == "get" and "/pets/{petId}" in path:
        return MOCK_FIRST_TEST_GET_BY_ID_RESPONSE
    return MOCK_FIRST_TEST_GET_RESPONSE


def get_mock_additional_tests():
    """Get mock additional tests response"""
    return MOCK_ADDITIONAL_TESTS_RESPONSE
