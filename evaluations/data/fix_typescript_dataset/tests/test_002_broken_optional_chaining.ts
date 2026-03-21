import { UserService } from '../models/services/UserService.js';
import { UserModel } from '../models/requests/UserModel.js';

describe('Create User', () => {
  const userService = new UserService();

  it('should create a user successfully', async () => {
    const user: UserModel = {
      name: `Test User ${Date.now()}`,
      email: `test${Date.now()}@example.com`,
      age: 30
    };

    const response = await userService.createUser<UserModel>(user);

    response.status.should.equal(201);
    response.data.name.should.equal(user.name);
    response.data.email.should.equal(user.email);
    response.data.age.should.equal(user.age);
  });
});
