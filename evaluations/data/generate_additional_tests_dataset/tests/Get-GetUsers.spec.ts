import { UserService } from "../../models/services/UserService.js";
import { UserListResponse } from "../../models/responses/UserListResponse.js";
import 'chai/register-should.js';

describe("Get Users", () => {
  const userService = new UserService();

  it("@Smoke - Get Users successfully - 200", async () => {
    const response = await userService.getUsers<UserListResponse>();

    response.status.should.equal(200, JSON.stringify(response.data));
    response.data?.data?.should.be.an('array');
    response.data?.total?.should.be.a('number');
    response.data?.total?.should.be.greaterThanOrEqual(0);

    if (response.data?.data && response.data.data.length > 0) {
      const firstUser = response.data.data[0];
      firstUser.id?.should.be.a('number');
      firstUser.name?.should.be.a('string');
      firstUser.email?.should.be.a('string');
    }
  });
});
