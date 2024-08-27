API Functionality
This API provides a set of endpoints to manage newsletter subscriptions and logs of subscription activities. The API is built using Flask and SQLAlchemy, with MySQL as the database. The functionality is divided into the following key areas:

1. Subscription Management
Subscribe to the Newsletter (POST /subscription)
Users can subscribe to the newsletter by providing their name and email.
If a user already exists in the database but had previously unsubscribed, their subscription is reactivated.
A log entry is created to record the subscription action.
View All Subscriptions (GET /subscriptions)
Fetch a list of all newsletter subscribers, including their names, email addresses, and unsubscribe statuses.
Update Subscription (PUT /subscription/<uuid>)
Allows updating the name and email address of an existing subscription based on its UUID.
An update log is recorded for this action.
Delete Subscription (DELETE /subscription/<email>)
Deletes a subscription from the database based on the email address.
Associated logs are also removed.

2. Log Management
View All Logs (GET /logs)
Retrieve all logs, which include details of subscription and unsubscription actions.
If an ID is provided as a query parameter (id=<log_uuid>), the API returns the log details for that specific log entry.
Create a Log (POST /log)
Manually create a log entry for subscription-related activities such as subscribing, unsubscribing, or updating a subscription.
The log entry includes details like the name, email, action type, timestamp, and associated subscription UUID.

3. Database Schema
Subscription Table
Fields include UUID, name, email, and unsubscribe status.
Log Table
Fields include UUID, name, email, action (subscribe/unsubscribe/update), timestamp, and a foreign key linking to the associated subscription.


4. Error Handling
The API handles various errors such as missing subscriptions, invalid UUIDs, and database connection issues.
Error messages are returned in a JSON format with appropriate HTTP status codes.
This API is designed to be straightforward and easy to integrate with a frontend application or other services that require newsletter management capabilities.

