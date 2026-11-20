// SPDX-License-Identifier: AGPL-3.0-only
// Run inside the exact SDK's packages/flutter/test/services directory.
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'autofill_test.dart' show FakeAutofillClient, FakeAutofillScope;
import 'text_input_utils.dart' show FakeTextChannel;

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  for (final learning in <bool>[false, true]) {
    test('AutofillScope preserves requested personalized learning: $learning', () {
      final channel = FakeTextChannel((MethodCall call) async {});
      TextInput.setChannel(channel);
      addTearDown(() {
        TextInputConnection.debugResetId();
        TextInput.setChannel(SystemChannels.textInput);
      });
      final client = FakeAutofillClient(TextEditingValue.empty);
      client.textInputConfiguration = TextInputConfiguration(
        obscureText: true,
        autocorrect: false,
        enableSuggestions: false,
        enableIMEPersonalizedLearning: learning,
        autofillConfiguration: AutofillConfiguration(
          uniqueIdentifier: client.autofillId,
          autofillHints: const <String>[AutofillHints.password],
          currentEditingValue: TextEditingValue.empty,
        ),
      );
      final scope = FakeAutofillScope()..register(client);
      client.currentAutofillScope = scope;
      scope.attach(client, client.textInputConfiguration);
      final call = channel.outgoingCalls.single;
      expect(call.method, 'TextInput.setClient');
      final config = (call.arguments as List<dynamic>)[1] as Map<String, dynamic>;
      expect(config['enableIMEPersonalizedLearning'], learning);
      expect(config['obscureText'], isTrue);
      expect(config['enableSuggestions'], isFalse);
      final fields = config['fields'] as List<Map<String, dynamic>>;
      expect(fields, hasLength(1));
      expect((fields.single['autofill'] as Map<String, dynamic>)['hints'],
          <String>[AutofillHints.password]);
    });
  }
}
