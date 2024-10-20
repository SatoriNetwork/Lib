
@app.route('/proposals/get', methods=['GET'])
def getProposals():
    ''' get all proposals '''
    try:
        from satoricentral import database
        df = database.read(query="select * from proposal;")
        proposals = '[]'
        if isinstance(df, pd.DataFrame) and len(df) > 0:
            proposals = df.to_json(orient='records')
        return proposals, 200
    except Exception as e:
        return str(e), 400


@app.route('/proposal/votes/get/<proposal>', methods=['GET'])
def getProposalVotes(proposal: str):
    ''' get all votes for a proposal '''
    try:
        from satoricentral import database
        df = database.read(
            query="""
            select v.proposal_id, v.vote, w.alias, w.address, w.vaultaddress, w.rewardaddress from vote as v
            inner join wallet as w on v.wallet_id = w.id
            where proposal_id = %s;""",
            params=[proposal])
        votes = '[]'
        if isinstance(df, pd.DataFrame) and len(df) > 0:
            votes = df.to_json(orient='records')
        return votes, 200
    except Exception as e:
        return str(e), 400


@app.route('/proposal/vote/submit', methods=['POST'])
@authenticate
@registered
def submitProposalVote(wallet: Wallet):
    ''' save a vote '''
    try:
        payload = json.loads(request.get_json() or '{}')
        # turn the data in to VoteSchema object, save to database
        proposalId = int(payload.get('proposal_id'))
        vote = payload.get('vote')
        from satoricentral import database
        df = database.read(
            query="select options, expires from proposal where id = %s;",
            params=[str(proposalId)])
        if (
            not isinstance(df, pd.DataFrame) or
            len(df) != 1 or
            'options' not in df.columns or
            'expires' not in df.columns
        ):
            raise Exception('proposal not found')
        options = json.loads(df['options'].values[0])
        if vote not in options:
            raise Exception('invalid vote')
        if dt.datetime.now(dt.timezone.utc) > df['expires'].values[0]:
            raise Exception('proposal expired')
        success = database.write(
            query="insert into vote (wallet_id, proposal_id, vote) values (%s, %s, %s);",
            params=[str(wallet.id), str(proposalId), vote])
        if success:
            return 'OK', 200
        return 'FAILED', 200
    except Exception as e:
        return str(e), 400


@app.route('/proposal/submit', methods=['POST'])
@authenticate
@registered
def submitProposal(wallet: Wallet):
    ''' save a proposal '''
    try:
        payload = json.loads(request.get_json() or '{}')
        
        # Validate required fields
        required_fields = ['title', 'description', 'options', 'expires']
        for field in required_fields:
            if field not in payload:
                raise ValueError(f"Missing required field: {field}")
        
        # Extract and validate data
        title = payload['title']
        description = payload['description']
        options = json.dumps(payload['options'])  # Ensure options are stored as JSON string
        expires = dt.datetime.fromisoformat(payload['expires'])
        
        if expires <= dt.datetime.now(dt.timezone.utc):
            raise ValueError("Expiration date must be in the future")
        
        # Insert proposal into database
        from satoricentral import database
        success = database.write(
            query="INSERT INTO proposal (wallet_id, title, description, options, expires) VALUES (%s, %s, %s, %s, %s);",
            params=[str(wallet.id), title, description, options, expires]
        )
        
        if success:
            return 'Proposal submitted successfully', 200
        else:
            return 'Failed to submit proposal', 500
    except Exception as e:
        return str(e), 400