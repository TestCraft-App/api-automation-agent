import { UserService } from "../../models/services/UserService.js";
import { UserModel } from "../../models/requests/UserModel.js";
import { UserResponse } from "../../models/responses/UserResponse.js";
import 'chai/register-should.js';

describe("Delete User", () => {
  const userService = new UserService();
  let userId: number;

  before(async () => {
    const userData: UserModel = {
      name: "John Doe",
      email: `user${Math.random().toString(36).substring(2, 15)}@test.com`,
      age: 30,
    };

    const createResponse = await userService.createUser<UserResponse>(userData);
    createResponse.status.should.equal(200, JSON.stringify(createResponse.data));
    userId = createResponse.data?.id;
  });

  it("@Smoke - Delete User successfully - 204", async () => {
    const response = await userService.deleteUser<null>(userId);
    response.status.should.equal(204, JSON.stringify(response.data));
  });
});
