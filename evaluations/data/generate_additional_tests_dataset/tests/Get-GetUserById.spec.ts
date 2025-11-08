import { UserService } from "../../models/services/UserService.js";
import { UserResponse } from "../../models/responses/UserResponse.js";
import 'chai/register-should.js';

describe("Get User By ID", () => {
  const userService = new UserService();
  let userId: number;

  before(async () => {
    // Using a known user ID for testing
    userId = 101;
  });

  it("@Smoke - Get User By ID successfully - 200", async () => {
    const response = await userService.getUserById<UserResponse>(userId);

    response.status.should.equal(200, JSON.stringify(response.data));
    response.data?.id?.should.equal(userId);
    response.data?.name?.should.not.be.empty;
    response.data?.email?.should.not.be.empty;
    response.data?.email?.should.include("@");
    response.data?.age?.should.be.greaterThanOrEqual(0);
    response.data?.age?.should.be.lessThanOrEqual(150);
  });
});
