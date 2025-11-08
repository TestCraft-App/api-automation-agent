import { UserService } from "../../models/services/UserService.js";
import { UserModel } from "../../models/requests/UserModel.js";
import { PatchUserModel } from "../../models/requests/PatchUserModel.js";
import { UserResponse } from "../../models/responses/UserResponse.js";
import 'chai/register-should.js';

describe("Patch User", () => {
  const userService = new UserService();
  let userId: number;
  let createdUser: UserResponse;

  before(async () => {
    const createUserResponse = await userService.createUser<UserResponse>({
      name: "John Doe",
      email: "john.doe@example.com",
      age: 30,
    });

    createdUser = createUserResponse.data;
    userId = createdUser.id;
  });

  it("@Smoke - Patch User successfully - 200", async () => {
    const patchData: PatchUserModel = {
      name: "Jane Doe",
      email: "jane.doe@example.com",
      age: 31,
    };

    const response = await userService.patchUser<UserResponse>(userId, patchData);

    response.status.should.equal(200, JSON.stringify(response.data));
    response.data?.id.should.equal(userId);
    response.data?.name.should.equal(patchData.name);
    response.data?.email.should.equal(patchData.email);
    response.data?.age?.should.equal(patchData.age);
  });
});
