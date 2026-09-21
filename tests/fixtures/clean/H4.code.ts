// Ids are opaque: the store rejects anything it did not mint.
export function getUser(id: string): User {
  return users[id];
}
