export type LoginRequest = {
  username: string;
  password: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
  user_name: string;
};

export type AuthStatusResponse = {
  user_name: string;
  authenticated: boolean;
};

export type ChangePasswordRequest = {
  current_password: string;
  new_password: string;
};
