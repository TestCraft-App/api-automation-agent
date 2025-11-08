import { UserService } from "../../models/services/UserService.js";
import { UserModel } from "../../models/requests/UserModel.js";
import 'chai/register-should.js';

describe("Create User", () => {
  const userService = new UserService();

  it("@Smoke - Create User successfully - 201", async () => {
    const userData: UserModel = {
      name: "John Doe",
      email: `john.doe.${Math.random().toString(36).substring(2, 15)}@example.com`,
      age: 30
    };

    const response = await userService.createUser<UserModel>(userData);

    response.status.should.equal(201, JSON.stringify(response.data));
    response.data?.name?.should.equal(userData.name);
    response.data?.email?.should.equal(userData.email);
    response.data?.age?.should.equal(userData.age);
    response.data?.id?.should.not.be.undefined;
  });
});
