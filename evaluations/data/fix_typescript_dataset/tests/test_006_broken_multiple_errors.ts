import { UserService } from '../models/services/UserService';
import { UserModel } from '../models/requests/UserModel';

describe('Create User', () => {
  const userService = new UserService();

  it('should create a user successfully', async () => {
    const user: UserModel = {
      name: `Test User ${Date.now()}`,
      email: `test${Date.now()}@example.com`,
      age: 28
    };

    const response = await userService.createUser<Response<UserModel>>(user);

    response.status.should.equal(201);
    response.data.name.should.equal(user.name);
    response.data.email.should.equal(user.email);
  });
});
