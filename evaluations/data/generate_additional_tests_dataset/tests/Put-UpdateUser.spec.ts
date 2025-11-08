import { UserService } from "../../models/services/UserService.js";
import { UserModel } from "../../models/requests/UserModel.js";
import { UpdateUserModel } from "../../models/requests/UpdateUserModel.js";
import { UserResponse } from "../../models/responses/UserResponse.js";
import 'chai/register-should.js';

describe("Update User", () => {
  const userService = new UserService();
  let userId: number;
  let createdUser: UserModel;

  before(async () => {
    // Create a user to update
    const createResponse = await userService.createUser<UserResponse>({
      id: Math.floor(Math.random() * 1000000),
      name: "John Doe",
      email: `john.doe.${Math.random().toString(36).substring(2, 9)}@example.com`,
      age: 30,
    });

    userId = createResponse.data?.id;
    createdUser = {
      id: createResponse.data?.id,
      name: createResponse.data?.name,
      email: createResponse.data?.email,
      age: createResponse.data?.age,
    };
  });

  it("@Smoke - Update User successfully - 200", async () => {
    const updatedData: UpdateUserModel = {
      name: "Jamie Rivera",
      email: `jamie.rivera.${Math.random().toString(36).substring(2, 9)}@example.com`,
      age: 41,
    };

    const response = await userService.updateUser<UserResponse>(userId, updatedData);

    response.status?.should.equal(200, JSON.stringify(response.data));
    response.data?.id?.should.equal(userId);
    response.data?.name?.should.equal(updatedData.name);
    response.data?.email?.should.equal(updatedData.email);
    response.data?.age?.should.equal(updatedData.age);
  });
});
