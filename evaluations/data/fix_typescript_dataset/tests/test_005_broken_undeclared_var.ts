import { UserService } from '../models/services/UserService.js';
import { UserModel } from '../models/requests/UserModel.js';

describe('Delete User', () => {
  const userService = new UserService();

  let createdUser: UserModel;

  before(async () => {
    const user: UserModel = {
      name: `Test User ${Date.now()}`,
      email: `test${Date.now()}@example.com`,
    };
    const response = await userService.createUser<UserModel>(user);
    createdUser = response.data;
  });

  it('should delete the user', async () => {
    const response = await userService.deleteUser(userId);
    response.status.should.equal(204);
  });
});
