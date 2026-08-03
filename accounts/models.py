# v1 uses Django's built-in auth.User as-is (username/password + email).
# No custom user model yet - if we need extra profile fields later (e.g.
# country, visa status), add a OneToOne "Profile" model here rather than
# swapping the User model after data exists.
